package dev.christiankfoury.aiplatform.security;

import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
public class KeyUsageRecorder {
  private final NamedParameterJdbcTemplate jdbc;

  public KeyUsageRecorder(NamedParameterJdbcTemplate jdbc) {
    this.jdbc = jdbc;
  }

  @Transactional(propagation = Propagation.MANDATORY)
  public void record(UUID keyId) {
    jdbc.update(
        """
        UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = :id AND is_active = true AND revoked_at IS NULL
          AND (last_used_at IS NULL OR last_used_at < CURRENT_TIMESTAMP - INTERVAL '1 minute')
        """,
        Map.of("id", keyId));
  }
}
