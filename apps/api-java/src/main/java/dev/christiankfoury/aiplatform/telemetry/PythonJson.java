package dev.christiankfoury.aiplatform.telemetry;

import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;

/** Exact compact ASCII JSON representation used by legacy Python replay fingerprints. */
public final class PythonJson {
  private static final char[] HEX = "0123456789abcdef".toCharArray();

  private PythonJson() {}

  public static String fingerprint(Object value) {
    try {
      return HexFormat.of()
          .formatHex(
              MessageDigest.getInstance("SHA-256")
                  .digest(encode(value).getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException exception) {
      throw new IllegalStateException("SHA-256 is unavailable", exception);
    }
  }

  public static String encode(Object value) {
    StringBuilder out = new StringBuilder();
    append(value, out);
    return out.toString();
  }

  private static void append(Object value, StringBuilder out) {
    if (value == null) {
      out.append("null");
    } else if (value instanceof String text) {
      string(text, out);
    } else if (value instanceof Boolean flag) {
      out.append(flag);
    } else if (value instanceof Double number) {
      out.append(floatText(number));
    } else if (value instanceof Float number) {
      out.append(floatText(number.doubleValue()));
    } else if (value instanceof Integer
        || value instanceof Long
        || value instanceof java.math.BigInteger) {
      out.append(value);
    } else if (value instanceof Map<?, ?> map) {
      List<String> keys = new ArrayList<>();
      for (Object key : map.keySet()) {
        if (!(key instanceof String text))
          throw new IllegalArgumentException("JSON keys must be strings");
        keys.add(text);
      }
      keys.sort(PythonJson::compareCodePoints);
      out.append('{');
      boolean first = true;
      for (String key : keys) {
        if (!first) out.append(',');
        first = false;
        string(key, out);
        out.append(':');
        append(map.get(key), out);
      }
      out.append('}');
    } else if (value instanceof List<?> list) {
      out.append('[');
      boolean first = true;
      for (Object item : list) {
        if (!first) out.append(',');
        first = false;
        append(item, out);
      }
      out.append(']');
    } else {
      throw new IllegalArgumentException("Unsupported fingerprint value type");
    }
  }

  private static void string(String text, StringBuilder out) {
    out.append((char) 34);
    for (int index = 0; index < text.length(); index++) {
      char c = text.charAt(index);
      switch (c) {
        case 34 -> out.append((char) 92).append((char) 34);
        case 92 -> out.append((char) 92).append((char) 92);
        case 8 -> out.append((char) 92).append('b');
        case 12 -> out.append((char) 92).append('f');
        case 10 -> out.append((char) 92).append('n');
        case 13 -> out.append((char) 92).append('r');
        case 9 -> out.append((char) 92).append('t');
        default -> {
          if (c < 32 || c >= 127)
            out.append((char) 92)
                .append('u')
                .append(HEX[c >>> 12])
                .append(HEX[(c >>> 8) & 15])
                .append(HEX[(c >>> 4) & 15])
                .append(HEX[c & 15]);
          else out.append(c);
        }
      }
    }
    out.append((char) 34);
  }

  private static int compareCodePoints(String left, String right) {
    int a = 0, b = 0;
    while (a < left.length() && b < right.length()) {
      int x = left.codePointAt(a), y = right.codePointAt(b);
      if (x != y) return Integer.compare(x, y);
      a += Character.charCount(x);
      b += Character.charCount(y);
    }
    return Integer.compare(left.length() - a, right.length() - b);
  }

  public static String floatText(double number) {
    if (!Double.isFinite(number))
      throw new IllegalArgumentException("Fingerprint numbers must be finite");
    if (number == 0) return Double.doubleToRawLongBits(number) < 0 ? "-0.0" : "0.0";
    boolean negative = number < 0;
    double magnitude = Math.abs(number);
    BigDecimal exact = new BigDecimal(magnitude), selected = null;
    // Find the closest shortest decimal that round-trips, including subnormal doubles.
    // This avoids JVM-specific minimum significant digits and exponent formatting.
    for (int precision = 1; precision <= 17 && selected == null; precision++) {
      BigDecimal rounded = exact.round(new MathContext(precision, RoundingMode.HALF_EVEN));
      BigDecimal unit =
          BigDecimal.ONE.scaleByPowerOfTen(rounded.precision() - rounded.scale() - precision);
      for (BigDecimal candidate : List.of(rounded, rounded.subtract(unit), rounded.add(unit))) {
        if (candidate.signum() <= 0
            || Double.doubleToRawLongBits(candidate.doubleValue())
                != Double.doubleToRawLongBits(magnitude)) continue;
        candidate = candidate.stripTrailingZeros();
        if (selected == null
            || candidate.subtract(exact).abs().compareTo(selected.subtract(exact).abs()) < 0
            || (candidate.subtract(exact).abs().compareTo(selected.subtract(exact).abs()) == 0
                && !candidate.unscaledValue().testBit(0))) selected = candidate;
      }
    }
    if (selected == null) throw new IllegalStateException("No round-trip decimal found");
    int exponent = selected.precision() - selected.scale() - 1;
    String prefix = negative ? "-" : "";
    if (exponent >= -4 && exponent < 16) {
      String text = selected.toPlainString();
      return prefix + text + (text.contains(".") ? "" : ".0");
    }
    String digits = selected.unscaledValue().abs().toString();
    String coefficient =
        digits.substring(0, 1) + (digits.length() > 1 ? "." + digits.substring(1) : "");
    int absolute = Math.abs(exponent);
    return prefix
        + coefficient
        + "e"
        + (exponent < 0 ? "-" : "+")
        + (absolute < 10 ? "0" : "")
        + absolute;
  }
}
