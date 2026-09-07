package dev.christiankfoury.aiplatform.persistence;

import java.net.URI;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
class LocalSeedConfiguration {
  @Bean
  @ConditionalOnProperty(name = "platform.seed.enabled", havingValue = "true")
  ApplicationRunner seedLocalData(
      DevelopmentSeeder seeder,
      @Value("${platform.environment}") String environment,
      @Value("${spring.datasource.url}") String url) {
    return args -> {
      String host =
          url.startsWith("jdbc:postgresql://") ? URI.create(url.substring(5)).getHost() : null;
      if (!"local".equals(environment)
          || host == null
          || !Set.of("localhost", "127.0.0.1", "[::1]").contains(host)) {
        throw new IllegalStateException(
            "Synthetic seeding requires a local environment and loopback database");
      }
      seeder.seed();
    };
  }
}
