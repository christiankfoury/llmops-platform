package dev.christiankfoury.aiplatform.observability;

import java.util.LinkedHashMap;
import java.util.Map;

public final class OperationalContext {
  private static final ThreadLocal<Map<String, String>> CURRENT = new ThreadLocal<>();

  private OperationalContext() {}

  public static Map<String, String> open() {
    var fields = new LinkedHashMap<String, String>();
    CURRENT.set(fields);
    return fields;
  }

  public static void put(String key, Object value) {
    if (CURRENT.get() != null && value != null) CURRENT.get().put(key, value.toString());
  }

  public static void close() {
    CURRENT.remove();
  }
}
