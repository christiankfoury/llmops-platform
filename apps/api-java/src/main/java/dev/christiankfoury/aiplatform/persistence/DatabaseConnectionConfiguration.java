package dev.christiankfoury.aiplatform.persistence;

import com.zaxxer.hikari.HikariDataSource;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.jdbc.autoconfigure.DataSourceProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;

@Configuration
@EnableConfigurationProperties(DataSourceProperties.class)
public class DatabaseConnectionConfiguration {
  @Bean
  @ConfigurationProperties("spring.datasource.hikari")
  HikariDataSource dataSource(DataSourceProperties properties, Environment environment) {
    DatabaseTransport.require(
        properties.getUrl(), environment.getProperty("platform.environment", "local"));
    return properties.initializeDataSourceBuilder().type(HikariDataSource.class).build();
  }
}
