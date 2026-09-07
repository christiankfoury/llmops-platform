// Test-only issuer for the packaged-service smoke. Never included in the application JAR.
// Generates an ephemeral RSA key; the private key is never written or logged.
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyPairGenerator;
import java.security.Signature;
import java.security.interfaces.RSAPublicKey;
import java.time.Instant;
import java.util.Arrays;
import java.util.Base64;
import java.util.concurrent.CountDownLatch;

class OperatorIdentityFixture {
  static String encode(byte[] value) { return Base64.getUrlEncoder().withoutPadding().encodeToString(value); }
  static String unsigned(java.math.BigInteger value) {
    byte[] bytes = value.toByteArray();
    return encode(bytes[0] == 0 ? Arrays.copyOfRange(bytes, 1, bytes.length) : bytes);
  }
  public static void main(String[] args) throws Exception {
    if (args.length != 1) throw new IllegalArgumentException("Choose a temporary fixture output file");
    var generator = KeyPairGenerator.getInstance("RSA"); generator.initialize(2048);
    var pair = generator.generateKeyPair(); var key = (RSAPublicKey) pair.getPublic();
    var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    String jwks = "{\"keys\":[{\"kty\":\"RSA\",\"kid\":\"packaged-fixture\",\"alg\":\"RS256\",\"use\":\"sig\",\"n\":\"" + unsigned(key.getModulus()) + "\",\"e\":\"" + unsigned(key.getPublicExponent()) + "\"}]}";
    server.createContext("/jwks", exchange -> {
      byte[] body = jwks.getBytes(StandardCharsets.UTF_8);
      exchange.getResponseHeaders().set("Content-Type", "application/json");
      exchange.sendResponseHeaders(200, body.length);
      try (var output = exchange.getResponseBody()) { output.write(body); }
    });
    server.start(); Runtime.getRuntime().addShutdownHook(new Thread(() -> server.stop(0)));
    long now = Instant.now().getEpochSecond();
    String claims = "{\"iss\":\"https://operator.fixture.invalid\",\"sub\":\"packaged-smoke\",\"aud\":\"https://api.fixture.invalid\",\"token_use\":\"access\",\"iat\":" + now + ",\"exp\":" + (now + 600) + "}";
    String payload = encode("{\"alg\":\"RS256\",\"kid\":\"packaged-fixture\"}".getBytes(StandardCharsets.UTF_8)) + "." + encode(claims.getBytes(StandardCharsets.UTF_8));
    var signer = Signature.getInstance("SHA256withRSA"); signer.initSign(pair.getPrivate()); signer.update(payload.getBytes(StandardCharsets.US_ASCII));
    String token = payload + "." + encode(signer.sign());
    String output = "{\"jwks_uri\":\"http://127.0.0.1:" + server.getAddress().getPort() + "/jwks\",\"token\":\"" + token + "\"}";
    Path target = Path.of(args[0]); Path temporary = target.resolveSibling(target.getFileName() + ".tmp");
    Files.writeString(temporary, output, StandardCharsets.UTF_8);
    Files.move(temporary, target, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
    new CountDownLatch(1).await();
  }
}
