package dev.christiankfoury.aiplatform.reliability;

import dev.christiankfoury.aiplatform.http.ApiFailure;
import java.util.List;
import java.util.UUID;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.dao.DataAccessException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Service;

@Service
@EnableConfigurationProperties(LimitsSettings.class)
public class RedisAdmission {
  public enum Traffic {
    GATEWAY,
    TELEMETRY,
    OPERATOR
  }

  private static final DefaultRedisScript<Long> SCRIPT =
      new DefaultRedisScript<>(
          """
      local current = tonumber(redis.call('GET', KEYS[1]) or '0')
      if current >= tonumber(ARGV[1]) then
        return math.max(redis.call('PTTL', KEYS[1]), 1)
      end
      local count = redis.call('INCR', KEYS[1])
      if count == 1 then redis.call('PEXPIRE', KEYS[1], ARGV[2]) end
      return 0
      """,
          Long.class);
  private final StringRedisTemplate redis;
  private final LimitsSettings settings;

  public RedisAdmission(StringRedisTemplate redis, LimitsSettings settings) {
    this.redis = redis;
    this.settings = settings;
  }

  public void global(Traffic traffic) {
    require("global:" + traffic.name(), settings.globalLimit());
  }

  public void key(Traffic traffic, UUID keyId) {
    if (traffic == Traffic.OPERATOR || keyId == null)
      throw new IllegalArgumentException("A trusted machine key is required");
    require(
        "key:" + traffic.name() + ":" + keyId,
        traffic == Traffic.GATEWAY ? settings.gatewayLimit() : settings.telemetryLimit());
  }

  private void require(String suffix, int maximum) {
    try {
      Long retry =
          redis.execute(
              SCRIPT,
              List.of(settings.namespace() + ":" + suffix),
              Integer.toString(maximum),
              Long.toString(settings.window().toMillis()));
      if (retry == null || retry < 0) throw new ApiFailure(503, "Dependency unavailable");
      if (retry > 0) throw new RateLimitFailure(retry);
    } catch (DataAccessException failure) {
      throw new ApiFailure(503, "Dependency unavailable");
    }
  }
}
