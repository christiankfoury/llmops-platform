package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.*;

import dev.christiankfoury.aiplatform.reliability.*;
import java.time.Duration;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.core.StringRedisTemplate;

@SpringBootTest
class RedisAdmissionTest extends PostgresTestSupport {
  @Autowired StringRedisTemplate redis;
  @Autowired LettuceConnectionFactory connectionFactory;
  @Autowired RedisSettings connectionSettings;

  LimitsSettings settings(int global, int key, Duration window) {
    return new LimitsSettings("limiter-" + UUID.randomUUID(), global, key, key, window, 32);
  }

  @Test
  void independentConnectionsShareAnAtomicSaturatingQuota() throws Exception {
    var settings = settings(37, 10, Duration.ofSeconds(60));
    var otherFactory =
        new LettuceConnectionFactory(
            new RedisStandaloneConfiguration(connectionSettings.host(), connectionSettings.port()),
            connectionFactory.getClientConfiguration());
    otherFactory.afterPropertiesSet();
    otherFactory.start();
    try (var workers = Executors.newFixedThreadPool(16)) {
      var first = new RedisAdmission(redis, settings);
      var second = new RedisAdmission(new StringRedisTemplate(otherFactory), settings);
      AtomicInteger accepted = new AtomicInteger();
      AtomicInteger rejected = new AtomicInteger();
      var tasks = new java.util.ArrayList<java.util.concurrent.Future<?>>();
      for (int index = 0; index < 320; index++) {
        RedisAdmission instance = index % 2 == 0 ? first : second;
        tasks.add(
            workers.submit(
                () -> {
                  try {
                    instance.global(RedisAdmission.Traffic.GATEWAY);
                    accepted.incrementAndGet();
                  } catch (RateLimitFailure failure) {
                    assertThat(failure.retryAfterSeconds()).isBetween(1L, 60L);
                    rejected.incrementAndGet();
                  }
                }));
      }
      for (var task : tasks) task.get(10, java.util.concurrent.TimeUnit.SECONDS);
      assertThat(accepted.get()).isEqualTo(37);
      assertThat(rejected.get()).isEqualTo(283);
      assertThat(redis.opsForValue().get(settings.namespace() + ":global:GATEWAY")).isEqualTo("37");
    } finally {
      otherFactory.destroy();
    }
  }

  @Test
  void rejectedRequestsDoNotExtendTheWindowAndExpiryRecovers() throws Exception {
    var settings = settings(2, 2, Duration.ofMillis(300));
    var limiter = new RedisAdmission(redis, settings);
    limiter.global(RedisAdmission.Traffic.TELEMETRY);
    limiter.global(RedisAdmission.Traffic.TELEMETRY);
    assertThatThrownBy(() -> limiter.global(RedisAdmission.Traffic.TELEMETRY))
        .isInstanceOf(RateLimitFailure.class);
    Thread.sleep(400);
    limiter.global(RedisAdmission.Traffic.TELEMETRY);
    assertThat(redis.opsForValue().get(settings.namespace() + ":global:TELEMETRY")).isEqualTo("1");
  }

  @Test
  void trustedKeyAndRouteQuotasStayIndependent() {
    var settings = settings(10, 1, Duration.ofSeconds(60));
    var limiter = new RedisAdmission(redis, settings);
    UUID key = UUID.randomUUID();
    limiter.key(RedisAdmission.Traffic.GATEWAY, key);
    assertThatThrownBy(() -> limiter.key(RedisAdmission.Traffic.GATEWAY, key))
        .isInstanceOf(RateLimitFailure.class);
    limiter.key(RedisAdmission.Traffic.TELEMETRY, key);
    limiter.key(RedisAdmission.Traffic.GATEWAY, UUID.randomUUID());
    assertThatThrownBy(() -> limiter.key(RedisAdmission.Traffic.OPERATOR, key))
        .isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void settingsRequireHostedTlsAuthAndBoundedAdmission() {
    assertThatThrownBy(
            () -> new RedisSettings("cache.example.invalid", 6379, "", "", false, "prod"))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(
            () -> new LimitsSettings("unsafe namespace", 1, 1, 1, Duration.ofSeconds(1), 32))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> new LimitsSettings("safe", 1, 1, 1, Duration.ZERO, 32))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> new LimitsSettings("safe", 1, 1, 1, Duration.ofSeconds(1), 49))
        .isInstanceOf(IllegalArgumentException.class);
  }
}
