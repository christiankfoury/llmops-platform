package dev.christiankfoury.aiplatform.gateway;

import org.springframework.stereotype.Component;

@Component
public class MockCompletionProvider implements CompletionProvider {
  @Override
  public Result complete(GatewayContext context, String input, int attempt) {
    if (input.contains("[simulate_timeout]"))
      throw new ProviderFailure(ProviderFailure.Kind.TIMEOUT);
    if (input.contains("[simulate_transient_failure]") && attempt == 1)
      throw new ProviderFailure(ProviderFailure.Kind.ERROR);
    if (input.contains("[simulate_failure]")) throw new ProviderFailure(ProviderFailure.Kind.ERROR);
    String output =
        "[mock:" + context.model() + "] " + context.promptContent() + " Input received: " + input;
    return new Result(output, tokens(context.promptContent()) + tokens(input), tokens(output));
  }

  static int tokens(String text) {
    // Python str.split treats Unicode whitespace and U+001C..001F as separators.
    int count = 0;
    boolean inWord = false;
    for (int point : text.codePoints().toArray()) {
      boolean separator =
          Character.isWhitespace(point) || Character.isSpaceChar(point) || point == 0x85;
      if (!separator && !inWord) count++;
      inWord = !separator;
    }
    return Math.max(1, count);
  }
}
