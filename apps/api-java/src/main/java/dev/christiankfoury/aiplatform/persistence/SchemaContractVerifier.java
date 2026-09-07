package dev.christiankfoury.aiplatform.persistence;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.io.IOException;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

/** Read-only schema comparison before explicitly transferring migration ownership. */
public final class SchemaContractVerifier {
  public record ColumnSpec(
      String name,
      String type,
      boolean nullable,
      @JsonProperty("server_default") String serverDefault) {}

  public record ConstraintSpec(
      String type, String name, List<String> columns, List<String> references, String ondelete) {}

  public record IndexSpec(String name, List<String> columns, boolean unique) {}

  public record TableSpec(
      List<ColumnSpec> columns, List<ConstraintSpec> constraints, List<IndexSpec> indexes) {
    TableSpec normalized() {
      return new TableSpec(
          columns.stream().sorted(Comparator.comparing(ColumnSpec::name)).toList(),
          constraints.stream().sorted(Comparator.comparing(ConstraintSpec::toString)).toList(),
          indexes.stream().sorted(Comparator.comparing(IndexSpec::name)).toList());
    }
  }

  private final Map<String, TableSpec> expected;
  private final Set<String> explicitConstraintNames = new HashSet<>();

  public SchemaContractVerifier() {
    try (var input = getClass().getResourceAsStream("/contracts/database-metadata.json")) {
      if (input == null) throw new IllegalStateException("Frozen schema contract is missing");
      expected =
          JsonMapper.builder()
              .build()
              .readValue(input, new TypeReference<Map<String, TableSpec>>() {});
      expected.replaceAll((name, table) -> table.normalized());
      expected
          .values()
          .forEach(
              table ->
                  table
                      .constraints()
                      .forEach(
                          constraint -> {
                            if (constraint.name() != null)
                              explicitConstraintNames.add(constraint.name());
                          }));
    } catch (IOException exception) {
      throw new IllegalStateException("Frozen schema contract cannot be read", exception);
    }
  }

  public void verify(Connection connection, String schema) throws SQLException {
    Map<String, TableSpec> actual = inspect(connection, schema);
    if (!expected.keySet().equals(actual.keySet())) {
      throw new IllegalStateException("Schema tables differ from the frozen Python contract");
    }
    for (String table : expected.keySet()) {
      if (!expected.get(table).equals(actual.get(table))) {
        throw new IllegalStateException("Schema differs from the frozen Python contract: " + table);
      }
    }
  }

  public Map<String, TableSpec> inspect(Connection connection, String schema) throws SQLException {
    checkSchemaName(schema);
    Map<String, TableSpec> tables = new TreeMap<>();
    try (ResultSet rows =
        connection
            .getMetaData()
            .getTables(null, pattern(connection, schema), "%", new String[] {"TABLE"})) {
      while (rows.next()) {
        String table = rows.getString("TABLE_NAME");
        if (Set.of("alembic_version", "flyway_schema_history").contains(table)) continue;
        tables.put(
            table,
            new TableSpec(
                    columns(connection, schema, table),
                    constraints(connection, schema, table),
                    indexes(connection, schema, table))
                .normalized());
      }
    }
    try (var query =
        connection.prepareStatement(
            """
        SELECT count(*) FROM pg_class r JOIN pg_namespace n ON n.oid=r.relnamespace
        WHERE n.nspname=? AND (r.relkind IN ('v','m','f','S','p') OR r.relrowsecurity OR r.relhasrules OR (r.relkind='r' AND r.relpersistence <> 'p')
          OR EXISTS (SELECT 1 FROM pg_inherits h WHERE h.inhrelid=r.oid OR h.inhparent=r.oid)
          OR EXISTS (SELECT 1 FROM pg_attribute a JOIN pg_type t ON t.oid=a.atttypid
            WHERE a.attrelid=r.oid AND a.attnum>0 AND NOT a.attisdropped AND a.attcollation<>t.typcollation)
          OR EXISTS (SELECT 1 FROM pg_trigger t WHERE t.tgrelid=r.oid AND NOT t.tgisinternal))
        """)) {
      query.setString(1, schema);
      try (var rows = query.executeQuery()) {
        rows.next();
        if (rows.getLong(1) != 0)
          throw new IllegalStateException("Unverified schema objects prevent adoption");
      }
    }
    return tables;
  }

  public static void checkSchemaName(String schema) {
    if (schema == null || !schema.matches("[a-z][a-z0-9_]{0,62}")) {
      throw new IllegalArgumentException("An explicit lowercase application schema is required");
    }
  }

  private static String pattern(Connection connection, String identifier) throws SQLException {
    String escape = connection.getMetaData().getSearchStringEscape();
    return identifier
        .replace(escape, escape + escape)
        .replace("_", escape + "_")
        .replace("%", escape + "%");
  }

  private List<ColumnSpec> columns(Connection connection, String schema, String table)
      throws SQLException {
    List<ColumnSpec> result = new ArrayList<>();
    try (var rows =
        connection
            .getMetaData()
            .getColumns(null, pattern(connection, schema), pattern(connection, table), "%")) {
      while (rows.next()) {
        if ("timestamptz".equals(rows.getString("TYPE_NAME"))
            && rows.getInt("DECIMAL_DIGITS") != 6) {
          throw new IllegalStateException("Altered timestamp precision prevents adoption");
        }
        String type =
            switch (rows.getString("TYPE_NAME")) {
              case "varchar" -> "VARCHAR(" + rows.getInt("COLUMN_SIZE") + ")";
              case "numeric" ->
                  "NUMERIC("
                      + rows.getInt("COLUMN_SIZE")
                      + ", "
                      + rows.getInt("DECIMAL_DIGITS")
                      + ")";
              case "int4" -> "INTEGER";
              case "bool" -> "BOOLEAN";
              case "timestamptz" -> "TIMESTAMP WITH TIME ZONE";
              default -> rows.getString("TYPE_NAME").toUpperCase(java.util.Locale.ROOT);
            };
        if ("YES".equals(rows.getString("IS_AUTOINCREMENT"))
            || "YES".equals(rows.getString("IS_GENERATEDCOLUMN"))) {
          throw new IllegalStateException("Unexpected generated column prevents adoption");
        }
        result.add(
            new ColumnSpec(
                rows.getString("COLUMN_NAME"),
                type,
                "YES".equals(rows.getString("IS_NULLABLE")),
                rows.getString("COLUMN_DEF")));
      }
    }
    return result;
  }

  private List<ConstraintSpec> constraints(Connection connection, String schema, String table)
      throws SQLException {
    List<ConstraintSpec> result = new ArrayList<>();
    try (var query =
        connection.prepareStatement(
            """
        SELECT c.conname,c.contype,c.confdeltype,c.condeferrable,c.condeferred,c.convalidated,c.confupdtype,c.confmatchtype,
          ft.relname AS foreign_table,fn.nspname AS foreign_schema,
          ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(id,pos)
            JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.id ORDER BY k.pos) AS columns,
          ARRAY(SELECT a.attname FROM unnest(c.confkey) WITH ORDINALITY k(id,pos)
            JOIN pg_attribute a ON a.attrelid=c.confrelid AND a.attnum=k.id ORDER BY k.pos) AS referenced_columns,
          coalesce(i.indnullsnotdistinct,false) AS nulls_not_distinct
        FROM pg_constraint c JOIN pg_class r ON r.oid=c.conrelid
          JOIN pg_namespace n ON n.oid=r.relnamespace
          LEFT JOIN pg_class ft ON ft.oid=c.confrelid LEFT JOIN pg_namespace fn ON fn.oid=ft.relnamespace
          LEFT JOIN pg_index i ON i.indexrelid=c.conindid
        WHERE n.nspname=? AND r.relname=?
        """)) {
      query.setString(1, schema);
      query.setString(2, table);
      try (var rows = query.executeQuery()) {
        while (rows.next()) {
          if (rows.getBoolean("condeferrable")
              || rows.getBoolean("condeferred")
              || !rows.getBoolean("convalidated")
              || rows.getBoolean("nulls_not_distinct")) {
            throw new IllegalStateException("Altered constraint semantics prevent adoption");
          }
          String type =
              switch (rows.getString("contype")) {
                case "p" -> "PrimaryKeyConstraint";
                case "u" -> "UniqueConstraint";
                case "f" -> "ForeignKeyConstraint";
                default ->
                    throw new IllegalStateException("Unexpected constraint prevents adoption");
              };
          String name = rows.getString("conname");
          List<String> references = null;
          String ondelete = null;
          if (type.equals("ForeignKeyConstraint")) {
            if (!"a".equals(rows.getString("confupdtype"))
                || !"s".equals(rows.getString("confmatchtype")))
              throw new IllegalStateException("Altered foreign-key update or match action");
            if (!schema.equals(rows.getString("foreign_schema")))
              throw new IllegalStateException("Cross-schema foreign key prevents adoption");
            String target = rows.getString("foreign_table");
            references =
                strings(rows, "referenced_columns").stream()
                    .map(column -> target + "." + column)
                    .toList();
            ondelete =
                switch (rows.getString("confdeltype")) {
                  case "c" -> "CASCADE";
                  case "r" -> "RESTRICT";
                  case "n" -> "SET NULL";
                  default ->
                      throw new IllegalStateException("Unexpected foreign-key delete action");
                };
          }
          result.add(
              new ConstraintSpec(
                  type,
                  explicitConstraintNames.contains(name) ? name : null,
                  strings(rows, "columns"),
                  references,
                  ondelete));
        }
      }
    }
    return result;
  }

  private List<IndexSpec> indexes(Connection connection, String schema, String table)
      throws SQLException {
    List<IndexSpec> result = new ArrayList<>();
    try (var query =
        connection.prepareStatement(
            """
        SELECT count(*) FROM pg_index i JOIN pg_class r ON r.oid=i.indrelid
          JOIN pg_namespace n ON n.oid=r.relnamespace
        WHERE n.nspname=? AND r.relname=? AND (
          i.indnatts<>i.indnkeyatts OR EXISTS (
            SELECT 1 FROM unnest(i.indkey) WITH ORDINALITY k(id,pos)
              LEFT JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.id
            WHERE a.attname IS NULL OR pg_get_indexdef(i.indexrelid,k.pos::int,true)<>quote_ident(a.attname)))
        """)) {
      query.setString(1, schema);
      query.setString(2, table);
      try (var rows = query.executeQuery()) {
        rows.next();
        if (rows.getLong(1) != 0)
          throw new IllegalStateException("Altered index definition prevents adoption");
      }
    }
    try (var query =
        connection.prepareStatement(
            """
        SELECT ix.relname,i.indisunique,i.indisvalid,i.indislive,i.indpred IS NULL AS unrestricted,
          i.indnullsnotdistinct,am.amname,
          ARRAY(SELECT a.attname FROM unnest(i.indkey) WITH ORDINALITY k(id,pos)
            LEFT JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.id ORDER BY k.pos) AS columns
        FROM pg_index i JOIN pg_class r ON r.oid=i.indrelid JOIN pg_namespace n ON n.oid=r.relnamespace
          JOIN pg_class ix ON ix.oid=i.indexrelid JOIN pg_am am ON am.oid=ix.relam
        WHERE n.nspname=? AND r.relname=? AND NOT EXISTS(SELECT 1 FROM pg_constraint c WHERE c.conindid=i.indexrelid)
        """)) {
      query.setString(1, schema);
      query.setString(2, table);
      try (var rows = query.executeQuery()) {
        while (rows.next()) {
          if (!rows.getBoolean("indisvalid")
              || !rows.getBoolean("indislive")
              || !rows.getBoolean("unrestricted")
              || rows.getBoolean("indnullsnotdistinct")
              || !"btree".equals(rows.getString("amname"))) {
            throw new IllegalStateException("Altered index semantics prevent adoption");
          }
          result.add(
              new IndexSpec(
                  rows.getString("relname"),
                  strings(rows, "columns"),
                  rows.getBoolean("indisunique")));
        }
      }
    }
    return result;
  }

  private static List<String> strings(ResultSet rows, String column) throws SQLException {
    var value = rows.getArray(column);
    try {
      return Arrays.stream((Object[]) value.getArray())
          .map(item -> item == null ? "<expression>" : item.toString())
          .toList();
    } finally {
      value.free();
    }
  }
}
