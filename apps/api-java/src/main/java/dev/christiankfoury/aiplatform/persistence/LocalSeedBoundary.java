package dev.christiankfoury.aiplatform.persistence;

import java.net.URI;
import java.util.Set;

public final class LocalSeedBoundary {
  private LocalSeedBoundary() {}

  public static void require(String environment, String url, boolean composeNetwork) {
    String host = null;
    try {
      if (url != null && url.startsWith("jdbc:postgresql://"))
        host = URI.create(url.substring(5)).getHost();
    } catch (IllegalArgumentException ignored) {
      /* Only a generic boundary error is returned. */
    }
    if (!"local".equals(environment)
        || host == null
        || !(Set.of("localhost", "127.0.0.1", "[::1]").contains(host)
            || composeNetwork && host.equals("postgres")))
      throw new IllegalArgumentException(
          "Synthetic seeding requires a local loopback database or explicitly enabled Compose postgres service");
  }
}
