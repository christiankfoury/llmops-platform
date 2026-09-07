package dev.christiankfoury.aiplatform.telemetry;

import dev.christiankfoury.aiplatform.http.ApiFailure;
import dev.christiankfoury.aiplatform.http.ValidationFailure;
import java.util.Map;
import tools.jackson.core.JacksonException;
import tools.jackson.core.StreamReadConstraints;
import tools.jackson.core.StreamReadFeature;
import tools.jackson.core.json.JsonFactory;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.json.JsonMapper;

public final class TelemetryJson {
  public static final int MAX_BODY_BYTES = 32768;
  private static final JsonMapper MAPPER =
      JsonMapper.builder(
              JsonFactory.builder()
                  .enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION)
                  .streamReadConstraints(
                      StreamReadConstraints.builder()
                          .maxNestingDepth(4)
                          .maxStringLength(8192)
                          .maxNumberLength(100)
                          .build())
                  .build())
          .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
          .build();

  private TelemetryJson() {}

  public static Map<String, Object> decode(byte[] body) {
    if (body.length > MAX_BODY_BYTES) throw new ApiFailure(413, "Telemetry payload too large");
    try {
      Map<String, Object> value =
          MAPPER.readValue(body, new TypeReference<Map<String, Object>>() {});
      if (value == null) throw new ValidationFailure(null);
      return value;
    } catch (JacksonException malformed) {
      throw new ValidationFailure(null);
    }
  }
}
