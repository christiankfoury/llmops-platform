package dev.christiankfoury.aiplatform;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import dev.christiankfoury.aiplatform.gateway.*;
import java.time.Duration;
import java.util.ArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class ProviderCallerTest {
  @Test
  void actualDeadlineCancelsSleepingProvider() throws Exception {
    CountDownLatch interrupted = new CountDownLatch(1);
    var caller =
        new ProviderCaller(
            (context, input, attempt) -> {
              try {
                Thread.sleep(10000);
              } catch (InterruptedException stopped) {
                interrupted.countDown();
                Thread.currentThread().interrupt();
              }
              return new CompletionProvider.Result("synthetic", 1, 1);
            },
            new ProviderSettings(1, Duration.ofMillis(100), Duration.ZERO, 1));
    try {
      long start = System.nanoTime();
      assertThatThrownBy(() -> caller.complete(null, "synthetic"))
          .isInstanceOfSatisfying(
              ProviderFailure.class,
              failure -> assertThat(failure.kind()).isEqualTo(ProviderFailure.Kind.TIMEOUT));
      assertThat(Duration.ofNanos(System.nanoTime() - start)).isLessThan(Duration.ofSeconds(2));
      assertThat(interrupted.await(1, TimeUnit.SECONDS)).isTrue();
    } finally {
      caller.shutdown();
    }
  }

  @Test
  void workerAndQueueCapacityRemainBounded() throws Exception {
    CountDownLatch entered = new CountDownLatch(1);
    CountDownLatch release = new CountDownLatch(1);
    CountDownLatch rejected = new CountDownLatch(1);
    AtomicInteger active = new AtomicInteger();
    AtomicInteger maxActive = new AtomicInteger();
    var caller =
        new ProviderCaller(
            (context, input, attempt) -> {
              maxActive.accumulateAndGet(active.incrementAndGet(), Math::max);
              entered.countDown();
              try {
                release.await(4, TimeUnit.SECONDS);
              } catch (InterruptedException stopped) {
                Thread.currentThread().interrupt();
              } finally {
                active.decrementAndGet();
              }
              return new CompletionProvider.Result("synthetic", 1, 1);
            },
            new ProviderSettings(1, Duration.ofSeconds(5), Duration.ZERO, 1));
    try (var senders = Executors.newVirtualThreadPerTaskExecutor()) {
      var results = new ArrayList<Future<?>>();
      try {
        for (int index = 0; index < 16; index++)
          results.add(
              senders.submit(
                  () -> {
                    try {
                      caller.complete(null, "synthetic");
                    } catch (ProviderFailure failure) {
                      if (failure.kind() == ProviderFailure.Kind.BUSY) rejected.countDown();
                      else throw failure;
                    }
                  }));
        assertThat(entered.await(2, TimeUnit.SECONDS)).isTrue();
        assertThat(rejected.await(2, TimeUnit.SECONDS)).isTrue();
      } finally {
        release.countDown();
      }
      for (var result : results) result.get(3, TimeUnit.SECONDS);
      assertThat(maxActive.get()).isEqualTo(1);
    } finally {
      caller.shutdown();
    }
  }

  @Test
  void pricingUsesDecimalHalfUpAndSettingsRejectUnboundedValues() {
    assertThat(MockPricing.cost(5, 0)).isEqualByComparingTo("0.000001");
    assertThat(MockPricing.cost(0, 0).toPlainString()).isEqualTo("0.000000");
    assertThatThrownBy(() -> new ProviderSettings(0, Duration.ofSeconds(1), Duration.ZERO, 1))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> new ProviderSettings(4, Duration.ofSeconds(1), Duration.ZERO, 1))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> new ProviderSettings(1, Duration.ofSeconds(61), Duration.ZERO, 1))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> new ProviderSettings(1, Duration.ofSeconds(1), Duration.ZERO, 100))
        .isInstanceOf(IllegalArgumentException.class);
  }
}
