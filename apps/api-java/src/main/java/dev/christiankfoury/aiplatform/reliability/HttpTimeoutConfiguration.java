package dev.christiankfoury.aiplatform.reliability;

import org.springframework.boot.tomcat.servlet.TomcatServletWebServerFactory;
import org.springframework.boot.web.server.WebServerFactoryCustomizer;
import org.springframework.stereotype.Component;

@Component
public class HttpTimeoutConfiguration
    implements WebServerFactoryCustomizer<TomcatServletWebServerFactory> {
  @Override
  public void customize(TomcatServletWebServerFactory factory) {
    factory.addConnectorCustomizers(
        connector -> {
          if (!connector.setProperty("disableUploadTimeout", "false")
              || !connector.setProperty("connectionUploadTimeout", "1000"))
            throw new IllegalStateException("Required HTTP body timeout could not be configured");
        });
  }
}
