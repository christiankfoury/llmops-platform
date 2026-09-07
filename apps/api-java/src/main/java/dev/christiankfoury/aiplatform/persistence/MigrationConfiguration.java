package dev.christiankfoury.aiplatform.persistence;

import org.springframework.boot.flyway.autoconfigure.FlywayMigrationStrategy;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
class MigrationConfiguration {
  @Bean
  FlywayMigrationStrategy verifiedMigrationStrategy() {
    return DatabaseMigrations::migrate;
  }
}
