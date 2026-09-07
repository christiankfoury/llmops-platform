package dev.christiankfoury.aiplatform.security;

import java.time.Clock;
import java.time.Duration;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.jwt.*;
import org.springframework.security.oauth2.server.resource.web.DefaultBearerTokenResolver;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.context.NullSecurityContextRepository;
import org.springframework.web.client.RestTemplate;

@Configuration
@EnableConfigurationProperties(OperatorSecuritySettings.class)
public class OperatorSecurityConfiguration {
  @Bean
  UserDetailsService noPasswordAccounts() {
    return username -> {
      throw new UsernameNotFoundException("Password authentication is unavailable");
    };
  }

  @Bean
  @ConditionalOnProperty(name = "operator.security.mode", havingValue = "oidc")
  JwtDecoder operatorJwtDecoder(OperatorSecuritySettings settings) {
    var factory = new SimpleClientHttpRequestFactory();
    factory.setConnectTimeout(Duration.ofSeconds(2));
    factory.setReadTimeout(Duration.ofSeconds(2));
    var decoder =
        NimbusJwtDecoder.withJwkSetUri(settings.jwksUri())
            .restOperations(new RestTemplate(factory))
            .build();
    decoder.setJwtValidator(
        new DelegatingOAuth2TokenValidator<>(
            new JwtIssuerValidator(settings.issuer()),
            new JwtTimestampValidator(Duration.ofSeconds(30)),
            new OperatorTokenValidator(settings.audience(), Clock.systemUTC())));
    return decoder;
  }

  @Bean
  SecurityFilterChain platformSecurity(
      HttpSecurity http, OperatorSecuritySettings settings, ObjectProvider<JwtDecoder> decoders)
      throws Exception {
    // The API accepts only explicit bearer/API-key headers, never browser session cookies.
    http.csrf(AbstractHttpConfigurer::disable)
        .formLogin(AbstractHttpConfigurer::disable)
        .httpBasic(AbstractHttpConfigurer::disable)
        .logout(AbstractHttpConfigurer::disable)
        .sessionManagement(
            session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
        .securityContext(
            context -> context.securityContextRepository(new NullSecurityContextRepository()))
        .requestCache(AbstractHttpConfigurer::disable)
        .exceptionHandling(
            errors ->
                errors
                    .authenticationEntryPoint(
                        (request, response, failure) -> {
                          response.setStatus(401);
                          response.setHeader("WWW-Authenticate", "Bearer");
                          response.setContentType("application/json");
                          response.getWriter().write("{\"detail\":\"Unauthorized\"}");
                        })
                    .accessDeniedHandler(
                        (request, response, failure) -> {
                          response.setStatus(403);
                          response.setContentType("application/json");
                          response.getWriter().write("{\"detail\":\"Forbidden\"}");
                        }))
        .authorizeHttpRequests(
            access -> {
              access.requestMatchers("/v1/usage/llm-events", "/v1/gateway/completions").permitAll();
              var operators =
                  access.requestMatchers("/v1/admin/**", "/v1/operator/**", "/v1/usage/**");
              if (settings.enabled()) operators.authenticated();
              else operators.denyAll();
              access
                  .anyRequest()
                  .permitAll(); // Unmapped routes retain safe 404s; health and machine routes own
              // their contracts.
            });
    if (settings.enabled()) {
      var resolver = new DefaultBearerTokenResolver();
      http.oauth2ResourceServer(
          resource ->
              resource
                  .bearerTokenResolver(
                      request -> {
                        String authorization = request.getHeader("Authorization");
                        if (authorization != null && authorization.length() > 8192)
                          throw new OAuth2AuthenticationException(
                              new OAuth2Error("invalid_token", "Invalid operator token", null));
                        return resolver.resolve(request);
                      })
                  .jwt(jwt -> jwt.decoder(decoders.getObject()))
                  .authenticationEntryPoint(
                      (request, response, failure) -> {
                        response.setStatus(401);
                        response.setHeader("WWW-Authenticate", "Bearer");
                        response.setContentType("application/json");
                        response.getWriter().write("{\"detail\":\"Unauthorized\"}");
                      }));
    }
    return http.build();
  }
}
