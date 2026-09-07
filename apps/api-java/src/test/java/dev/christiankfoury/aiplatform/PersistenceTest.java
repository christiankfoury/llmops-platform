package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import dev.christiankfoury.aiplatform.persistence.DevelopmentSeeder;
import dev.christiankfoury.aiplatform.persistence.model.GatewayRequest;
import dev.christiankfoury.aiplatform.persistence.repository.ApiKeyRepository;
import dev.christiankfoury.aiplatform.persistence.repository.ClientApplicationRepository;
import dev.christiankfoury.aiplatform.persistence.repository.GatewayRequestRepository;
import dev.christiankfoury.aiplatform.persistence.repository.ProjectRepository;
import jakarta.persistence.EntityManager;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.UUID;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

@SpringBootTest
class PersistenceTest extends PostgresTestSupport {
  @Autowired private DataSource dataSource;
  @Autowired private DevelopmentSeeder seeder;
  @Autowired private ProjectRepository projects;
  @Autowired private ClientApplicationRepository applications;
  @Autowired private ApiKeyRepository keys;
  @Autowired private GatewayRequestRepository requests;
  @Autowired private PlatformTransactionManager transactionManager;
  @Autowired private EntityManager entityManager;

  @Test
  void seedIsIdempotentAndPreservesRevocation() throws Exception {
    seeder.seed();
    var identifiers = projects.findAll().stream().map(project -> project.getId()).sorted().toList();
    var key = keys.findAll().getFirst();
    key.setRevokedAt(OffsetDateTime.parse("2026-01-02T00:00:00Z"));
    keys.saveAndFlush(key);
    seeder.seed();
    assertThat(projects.findAll().stream().map(project -> project.getId()).sorted().toList())
        .isEqualTo(identifiers);
    assertThat(projects.count()).isEqualTo(3);
    assertThat(applications.count()).isEqualTo(3);
    assertThat(keys.count()).isEqualTo(3);
    assertThat(keys.findById(key.getId()).orElseThrow().getRevokedAt()).isNotNull();
    assertThat(keys.findAll())
        .allSatisfy(item -> assertThat(item.getKeyHash()).matches("[a-f0-9]{64}"));
    try (var connection = dataSource.getConnection();
        var statement = connection.createStatement();
        var rows = statement.executeQuery("SELECT count(*) FROM operator_project_grants")) {
      rows.next();
      assertThat(rows.getInt(1)).isZero();
    }
  }

  @Test
  void jsonMoneyAndTimestampRoundTripAndTransactionRollback() {
    seeder.seed();
    var project = projects.findBySlug("demo-project").orElseThrow();
    var application =
        applications.findByProjectIdAndSlug(project.getId(), "demo-app").orElseThrow();
    String eventId = "roundtrip_" + UUID.randomUUID();
    TransactionTemplate transaction = new TransactionTemplate(transactionManager);
    UUID id =
        transaction.execute(
            status -> {
              GatewayRequest request = new GatewayRequest();
              request.setProjectId(project.getId());
              request.setApplicationId(application.getId());
              request.setRequestId(eventId);
              request.setExternalEventId(eventId);
              request.setStatus("succeeded");
              request.setEstimatedCostUsd(new BigDecimal("1.234567"));
              request.setExternalMetadataJson(Map.of("synthetic", true, "metadata.retry_count", 2));
              request.setCreatedAt(OffsetDateTime.parse("2026-01-02T03:04:05.123456Z"));
              requests.saveAndFlush(request);
              entityManager.clear();
              return request.getId();
            });
    var stored = requests.findById(id).orElseThrow();
    assertThat(stored.getEstimatedCostUsd()).isEqualByComparingTo("1.234567");
    assertThat(stored.getExternalMetadataJson())
        .containsEntry("synthetic", true)
        .containsEntry("metadata.retry_count", 2);
    assertThat(stored.getCreatedAt().toInstant())
        .isEqualTo(OffsetDateTime.parse("2026-01-02T03:04:05.123456Z").toInstant());
    long count = requests.count();
    assertThatThrownBy(
            () ->
                transaction.execute(
                    status -> {
                      GatewayRequest duplicate = new GatewayRequest();
                      duplicate.setProjectId(project.getId());
                      duplicate.setApplicationId(application.getId());
                      duplicate.setRequestId("unique_" + UUID.randomUUID());
                      duplicate.setExternalEventId(eventId);
                      requests.saveAndFlush(duplicate);
                      return null;
                    }))
        .isInstanceOf(org.springframework.dao.DataIntegrityViolationException.class);
    assertThat(requests.count()).isEqualTo(count);
  }
}
