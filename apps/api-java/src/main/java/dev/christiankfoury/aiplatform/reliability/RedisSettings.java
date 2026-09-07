package dev.christiankfoury.aiplatform.reliability;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("platform.redis")
public record RedisSettings(
    String host, int port, String username, String password, boolean tls, String environment) {
  public RedisSettings {
    if (host == null
        || host.isBlank()
        || host.length() > 253
        || host.codePoints().anyMatch(Character::isWhitespace)
        || port < 1
        || port > 65535
        || username == null
        || username.length() > 255
        || password == null
        || password.length() > 4096)
      throw new IllegalArgumentException("Invalid Redis connection settings");
    if (!java.util.Set.of("local", "test").contains(environment) && (!tls || password.isBlank()))
      throw new IllegalArgumentException("Hosted Redis requires verified TLS and authentication");
  }

  @Override
  public String toString() {
    return "RedisSettings[connection and credentials omitted]";
  }
}
