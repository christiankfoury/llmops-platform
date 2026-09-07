import java.net.HttpURLConnection;
import java.net.URI;

/** Container-local readiness check; never prints response or exception content. */
public final class HttpProbe {
  private HttpProbe() {}
  public static void main(String[] args) {
    try {
      String mode = args.length == 0 ? "ready" : args[0];
      if (!java.util.Set.of("ready", "live", "metrics").contains(mode)) System.exit(2);
      int port = Integer.parseInt(System.getenv().getOrDefault(mode.equals("metrics") ? "MANAGEMENT_PORT" : "PORT", mode.equals("metrics") ? "9080" : "8000"));
      String path = mode.equals("metrics") ? "/actuator/prometheus" : "/health/" + mode;
      var connection = (HttpURLConnection) URI.create("http://127.0.0.1:" + port + path).toURL().openConnection();
      connection.setConnectTimeout(1000); connection.setReadTimeout(1000);
      int status = connection.getResponseCode();
      if (status == 200 && mode.equals("metrics")) {
        byte[] body = connection.getInputStream().readNBytes(2_000_001);
        if (body.length > 2_000_000) System.exit(1);
        System.out.print(new String(body, java.nio.charset.StandardCharsets.UTF_8));
      }
      connection.disconnect();
      System.exit(status == 200 ? 0 : 1);
    } catch (Exception failure) { System.exit(1); }
  }
}
