package dev.christiankfoury.aiplatform.persistence;

import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Set;

public final class DatabaseTransport {
  private DatabaseTransport() {}

  public static void require(String url, String environment) {
    if (Set.of("local", "test").contains(environment)) return;
    try {
      if (url == null || !url.startsWith("jdbc:postgresql://"))
        throw new IllegalArgumentException();
      var uri = URI.create(url.substring(5));
      if (uri.getHost() == null || uri.getUserInfo() != null || uri.getFragment() != null)
        throw new IllegalArgumentException();
      var params = new HashMap<String, String>();
      for (String pair : (uri.getRawQuery() == null ? "" : uri.getRawQuery()).split("&")) {
        String[] parts = pair.split("=", 2);
        String key = URLDecoder.decode(parts[0], StandardCharsets.UTF_8);
        String value = parts.length == 2 ? URLDecoder.decode(parts[1], StandardCharsets.UTF_8) : "";
        if (params.putIfAbsent(key, value) != null) throw new IllegalArgumentException();
      }
      if (!"verify-full".equals(params.get("sslmode"))
          || params.containsKey("user")
          || params.containsKey("password")
          || params.containsKey("sslhostnameverifier")
          || params.containsKey("sslfactoryarg")
          || params.containsKey("sslpassword")) throw new IllegalArgumentException();
      String factory = params.get("sslfactory");
      if (factory != null
          && !Set.of("org.postgresql.ssl.LibPQFactory", "org.postgresql.ssl.DefaultJavaSSLFactory")
              .contains(factory)) throw new IllegalArgumentException();
    } catch (IllegalArgumentException failure) {
      throw new IllegalArgumentException(
          "Hosted PostgreSQL requires verify-full TLS, verified trust and separate credentials");
    }
  }
}
