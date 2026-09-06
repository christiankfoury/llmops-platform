package dev.christiankfoury.aiplatform.http;

import java.math.BigDecimal;
import org.springframework.boot.jackson.JacksonComponent;
import tools.jackson.core.JsonGenerator;
import tools.jackson.databind.SerializationContext;
import tools.jackson.databind.ValueSerializer;

/** Preserve the existing API's decimal-string wire format without binary floating point. */
@JacksonComponent
public class DecimalSerializer extends ValueSerializer<BigDecimal> {
  @Override
  public void serialize(BigDecimal value, JsonGenerator generator, SerializationContext context) {
    generator.writeString(value.toPlainString());
  }
}
