package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.nimbusds.jose.*;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jose.jwk.*;
import com.nimbusds.jose.jwk.gen.RSAKeyGenerator;
import com.nimbusds.jwt.*;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;
import java.util.function.Consumer;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class OperatorJwtHttpTest extends PostgresTestSupport {
  static final String ISSUER = "https://issuer.fixture.invalid";
  static final String AUDIENCE = "https://api.fixture.invalid";
  static final RSAKey KEY = key();
  static final HttpServer JWKS = server();
  @Autowired MockMvc http;

  static RSAKey key() {
    try {
      return new RSAKeyGenerator(2048).keyID("fixture-rsa").generate();
    } catch (JOSEException failure) {
      throw new IllegalStateException(failure);
    }
  }

  static HttpServer server() {
    try {
      var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
      byte[] body = new JWKSet(KEY.toPublicJWK()).toString().getBytes(StandardCharsets.UTF_8);
      server.createContext(
          "/jwks",
          exchange -> {
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, body.length);
            try (var output = exchange.getResponseBody()) {
              output.write(body);
            }
          });
      server.start();
      Runtime.getRuntime().addShutdownHook(new Thread(() -> server.stop(0)));
      return server;
    } catch (java.io.IOException failure) {
      throw new IllegalStateException(failure);
    }
  }

  @DynamicPropertySource
  static void security(DynamicPropertyRegistry registry) {
    registry.add("operator.security.mode", () -> "oidc");
    registry.add("operator.security.issuer", () -> ISSUER);
    registry.add("operator.security.audience", () -> AUDIENCE);
    registry.add(
        "operator.security.jwks-uri",
        () -> "http://127.0.0.1:" + JWKS.getAddress().getPort() + "/jwks");
  }

  static String token(Consumer<JWTClaimsSet.Builder> customize, RSAKey key) throws JOSEException {
    var claims =
        new JWTClaimsSet.Builder()
            .issuer(ISSUER)
            .subject("synthetic-signed-operator")
            .audience(AUDIENCE)
            .issueTime(Date.from(Instant.now().minusSeconds(1)))
            .expirationTime(Date.from(Instant.now().plusSeconds(300)))
            .claim("token_use", "access");
    customize.accept(claims);
    var signed =
        new SignedJWT(
            new JWSHeader.Builder(JWSAlgorithm.RS256).keyID(KEY.getKeyID()).build(),
            claims.build());
    signed.sign(new RSASSASigner(key));
    return signed.serialize();
  }

  @Test
  void signedIdentityAuthenticatesButDoesNotInventProjectGrants() throws Exception {
    String token =
        token(
            c ->
                c.claim("roles", java.util.List.of("operator"))
                    .claim("project_ids", java.util.List.of("*")),
            KEY);
    http.perform(get("/v1/operator/me").header("Authorization", "Bearer " + token))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.authenticated").value(true))
        .andExpect(jsonPath("$.projects").isEmpty());
    http.perform(get("/v1/usage/scopes").header("Authorization", "Bearer " + token))
        .andExpect(status().isOk())
        .andExpect(content().json("[]"));
  }

  @ParameterizedTest
  @ValueSource(
      strings = {
        "issuer",
        "audience",
        "expired",
        "future-iat",
        "future-nbf",
        "no-exp",
        "no-iat",
        "no-sub",
        "control-sub",
        "id-token",
        "bad-signature"
      })
  void rejectsInvalidSignedTokens(String problem) throws Exception {
    String token =
        token(
            c -> {
              switch (problem) {
                case "issuer" -> c.issuer("https://attacker.invalid");
                case "audience" -> c.audience("another-api");
                case "expired" -> c.expirationTime(Date.from(Instant.now().minusSeconds(90)));
                case "future-iat" -> c.issueTime(Date.from(Instant.now().plusSeconds(120)));
                case "future-nbf" -> c.notBeforeTime(Date.from(Instant.now().plusSeconds(120)));
                case "no-exp" -> c.expirationTime(null);
                case "no-iat" -> c.issueTime(null);
                case "no-sub" -> c.subject(null);
                case "control-sub" -> c.subject("bad\nsubject");
                case "id-token" -> c.claim("token_use", "id");
                default -> {}
              }
            },
            problem.equals("bad-signature") ? key() : KEY);
    var result =
        http.perform(get("/v1/usage/summary").header("Authorization", "Bearer " + token))
            .andExpect(status().isUnauthorized())
            .andExpect(content().json("{\"detail\":\"Unauthorized\"}"));
    assertThat(result.andReturn().getResponse().getContentAsString()).doesNotContain(token);
  }

  @ParameterizedTest
  @ValueSource(
      strings = {
        "not-a-jwt",
        "eyJhbGciOiJub25lIn0.eyJzdWIiOiJhZG1pbiJ9.",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbiJ9.c2ln"
      })
  void rejectsMalformedAndUntrustedAlgorithms(String token) throws Exception {
    http.perform(get("/v1/operator/me").header("Authorization", "Bearer " + token))
        .andExpect(status().isUnauthorized());
  }

  @Test
  void cookiesMachineKeysAndQueryTokensNeverAuthenticateOperators() throws Exception {
    String token = token(c -> {}, KEY);
    http.perform(
            get("/v1/usage/summary")
                .param("access_token", token)
                .cookie(new jakarta.servlet.http.Cookie("session", token))
                .header("X-API-Key", "local-dev-placeholder-key-not-a-secret"))
        .andExpect(status().isUnauthorized());
  }
}
