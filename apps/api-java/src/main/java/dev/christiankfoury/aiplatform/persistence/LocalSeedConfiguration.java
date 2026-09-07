package dev.christiankfoury.aiplatform.persistence;

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
      @Value("${spring.datasource.url}") String url,
      @Value("${platform.seed.allow-compose-network:false}") boolean composeNetwork) {
    return args -> {
      LocalSeedBoundary.require(environment, url, composeNetwork);
      seeder.seed();
    };
  }
}
