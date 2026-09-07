package dev.christiankfoury.aiplatform.reliability;

import io.lettuce.core.ClientOptions;
import io.lettuce.core.SocketOptions;
import io.lettuce.core.TimeoutOptions;
import io.lettuce.core.resource.ClientResources;
import io.lettuce.core.resource.DefaultClientResources;
import java.time.Duration;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceClientConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;

@Configuration
@EnableConfigurationProperties(RedisSettings.class)
public class RedisConfiguration {
  @Bean(destroyMethod = "shutdown")
  ClientResources redisClientResources() {
    return DefaultClientResources.builder()
        .ioThreadPoolSize(2)
        .computationThreadPoolSize(2)
        .build();
  }

  @Bean
  LettuceConnectionFactory redisConnectionFactory(
      RedisSettings settings, ClientResources resources) {
    var standalone = new RedisStandaloneConfiguration(settings.host(), settings.port());
    if (!settings.username().isBlank()) standalone.setUsername(settings.username());
    if (!settings.password().isBlank()) standalone.setPassword(settings.password());
    var options =
        ClientOptions.builder()
            .autoReconnect(true)
            .disconnectedBehavior(ClientOptions.DisconnectedBehavior.REJECT_COMMANDS)
            .requestQueueSize(64)
            .timeoutOptions(TimeoutOptions.enabled(Duration.ofMillis(500)))
            .socketOptions(SocketOptions.builder().connectTimeout(Duration.ofMillis(500)).build())
            .build();
    var client =
        LettuceClientConfiguration.builder()
            .clientResources(resources)
            .clientOptions(options)
            .commandTimeout(Duration.ofMillis(500))
            .shutdownTimeout(Duration.ofMillis(100))
            .shutdownQuietPeriod(Duration.ZERO);
    if (settings.tls())
      client.useSsl(); // Default certificate and hostname verification remain enabled.
    return new LettuceConnectionFactory(standalone, client.build());
  }
}
