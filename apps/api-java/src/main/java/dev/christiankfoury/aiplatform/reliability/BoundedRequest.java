package dev.christiankfoury.aiplatform.reliability;

import jakarta.servlet.ReadListener;
import jakarta.servlet.ServletInputStream;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletRequestWrapper;
import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

final class BoundedRequest extends HttpServletRequestWrapper {
  private final byte[] body;

  BoundedRequest(HttpServletRequest request, byte[] body) {
    super(request);
    this.body = body;
  }

  @Override
  public int getContentLength() {
    return body.length;
  }

  @Override
  public long getContentLengthLong() {
    return body.length;
  }

  @Override
  public ServletInputStream getInputStream() {
    var bytes = new ByteArrayInputStream(body);
    return new ServletInputStream() {
      @Override
      public int read() {
        return bytes.read();
      }

      @Override
      public int read(byte[] target, int offset, int length) {
        return bytes.read(target, offset, length);
      }

      @Override
      public boolean isFinished() {
        return bytes.available() == 0;
      }

      @Override
      public boolean isReady() {
        return true;
      }

      @Override
      public void setReadListener(ReadListener listener) {
        throw new IllegalStateException("Only bounded synchronous API bodies are supported");
      }
    };
  }

  @Override
  public BufferedReader getReader() {
    return new BufferedReader(new InputStreamReader(getInputStream(), StandardCharsets.UTF_8));
  }
}
