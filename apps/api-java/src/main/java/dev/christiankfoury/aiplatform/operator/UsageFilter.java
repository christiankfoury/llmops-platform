package dev.christiankfoury.aiplatform.operator;

import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;

public record UsageFilter(String where, MapSqlParameterSource parameters, int limit) {
  private static final Map<String, Integer> TEXT =
      Map.of(
          "status",
          40,
          "provider",
          80,
          "model_name",
          160,
          "source_app",
          80,
          "operation_type",
          80,
          "error_category",
          80);
  private static final Set<String> FIELDS =
      Set.of(
          "project_id",
          "application_id",
          "status",
          "provider",
          "model_name",
          "source_app",
          "operation_type",
          "error_category",
          "created_from",
          "created_to",
          "limit");

  public static UsageFilter parse(Map<String, String[]> query, boolean errorsOnly) {
    List<String> predicates = new ArrayList<>();
    MapSqlParameterSource values = new MapSqlParameterSource();
    for (var entry : query.entrySet()) {
      String name = entry.getKey();
      if (!FIELDS.contains(name)) throw invalid(null);
      if (entry.getValue().length != 1) throw invalid(name);
    }
    for (String name : List.of("project_id", "application_id")) {
      String value = single(query, name);
      if (value == null) continue;
      try {
        if (!value.matches(
            "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"))
          throw invalid(name);
        values.addValue(name, UUID.fromString(value));
      } catch (IllegalArgumentException failure) {
        throw invalid(name);
      }
      predicates.add("r." + name + " = :" + name);
    }
    for (var field : TEXT.entrySet()) {
      String name = field.getKey(), value = single(query, name);
      if (value == null) continue;
      if (value.codePointCount(0, value.length()) > field.getValue() || value.indexOf(0) >= 0)
        throw invalid(name);
      if (value.isEmpty() || (errorsOnly && name.equals("status"))) continue;
      predicates.add("r." + name + " = :" + name);
      values.addValue(name, value);
    }
    OffsetDateTime from = date(single(query, "created_from"), "created_from");
    OffsetDateTime to = date(single(query, "created_to"), "created_to");
    if (from != null && to != null && from.isAfter(to)) throw invalid("created_to");
    if (from != null) {
      predicates.add("r.created_at >= :created_from");
      values.addValue("created_from", from);
    }
    if (to != null) {
      predicates.add("r.created_at <= :created_to");
      values.addValue("created_to", to);
    }
    if (errorsOnly) predicates.add("r.status = 'failed'");
    int limit = limit(single(query, "limit"), 20);
    values.addValue("limit", limit);
    return new UsageFilter(
        predicates.isEmpty() ? "" : " WHERE " + String.join(" AND ", predicates), values, limit);
  }

  public static int limit(String value, int fallback) {
    if (value == null) return fallback;
    try {
      if (!value.matches("[0-9]{1,20}")) throw invalid("limit");
      var number = new java.math.BigInteger(value);
      if (number.signum() <= 0) throw invalid("limit");
      return number.min(java.math.BigInteger.valueOf(100)).intValueExact();
    } catch (NumberFormatException failure) {
      throw invalid("limit");
    }
  }

  private static OffsetDateTime date(String value, String field) {
    if (value == null) return null;
    try {
      if (value.length() > 64) throw invalid(field);
      OffsetDateTime result =
          OffsetDateTime.parse(value).truncatedTo(java.time.temporal.ChronoUnit.MICROS);
      if (result.getYear() < 1 || result.getYear() > 9999) throw invalid(field);
      return result;
    } catch (DateTimeParseException failure) {
      throw invalid(field);
    }
  }

  private static String single(Map<String, String[]> query, String name) {
    return query.containsKey(name) ? query.get(name)[0] : null;
  }

  private static OperatorValidationFailure invalid(String field) {
    return new OperatorValidationFailure("query", field);
  }
}
