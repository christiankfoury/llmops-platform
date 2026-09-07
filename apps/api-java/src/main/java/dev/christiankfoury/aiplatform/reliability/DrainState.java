package dev.christiankfoury.aiplatform.reliability;

import java.util.concurrent.atomic.AtomicBoolean;
import org.springframework.context.event.ContextClosedEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class DrainState {
  private final AtomicBoolean draining = new AtomicBoolean();

  public boolean draining() {
    return draining.get();
  }

  public void begin() {
    draining.set(true);
  }

  @EventListener(ContextClosedEvent.class)
  public void closing() {
    begin();
  }
}
