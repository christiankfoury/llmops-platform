package dev.christiankfoury.aiplatform.observability;

import org.springframework.boot.actuate.autoconfigure.web.server.ManagementPortType;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

@Component
public class ManagementListenerGuard {
  public ManagementListenerGuard(Environment environment) {
    if (ManagementPortType.get(environment) != ManagementPortType.DIFFERENT)
      throw new IllegalArgumentException("Actuator must use a separate management listener");
  }
}
