package dev.christiankfoury.aiplatform.gateway;

import jakarta.annotation.PreDestroy;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.CancellationException;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.stereotype.Service;

@Service
@EnableConfigurationProperties(ProviderSettings.class)
public class ProviderCaller {
  private final CompletionProvider provider;
  private final ProviderSettings settings;
  private final ThreadPoolExecutor workers;

  public ProviderCaller(CompletionProvider provider, ProviderSettings settings) {
    this.provider = provider;
    this.settings = settings;
    workers =
        new ThreadPoolExecutor(
            settings.concurrency(),
            settings.concurrency(),
            0,
            TimeUnit.MILLISECONDS,
            new ArrayBlockingQueue<>(settings.concurrency()),
            Thread.ofPlatform().daemon(true).name("mock-provider-", 0).factory(),
            new ThreadPoolExecutor.AbortPolicy());
  }

  public CompletionProvider.Result complete(GatewayContext context, String input) {
    long deadline = System.nanoTime() + settings.timeout().toNanos();
    for (int attempt = 1; attempt <= settings.maxAttempts(); attempt++) {
      try {
        return attempt(context, input, attempt, deadline);
      } catch (ProviderFailure failure) {
        if (!failure.kind().retryable() || attempt == settings.maxAttempts()) throw failure;
        try {
          long remaining = deadline - System.nanoTime();
          if (remaining <= settings.retryBackoff().toNanos())
            throw new ProviderFailure(ProviderFailure.Kind.TIMEOUT);
          Thread.sleep(settings.retryBackoff());
        } catch (InterruptedException interrupted) {
          Thread.currentThread().interrupt();
          throw new ProviderFailure(ProviderFailure.Kind.INTERRUPTED);
        }
      }
    }
    throw new ProviderFailure(ProviderFailure.Kind.ERROR);
  }

  private CompletionProvider.Result attempt(
      GatewayContext context, String input, int attempt, long deadline) {
    long remaining = deadline - System.nanoTime();
    if (remaining <= 0) throw new ProviderFailure(ProviderFailure.Kind.TIMEOUT);
    java.util.concurrent.Future<CompletionProvider.Result> task;
    try {
      task = workers.submit(() -> provider.complete(context, input, attempt));
    } catch (RejectedExecutionException busy) {
      throw new ProviderFailure(ProviderFailure.Kind.BUSY);
    }
    try {
      remaining = deadline - System.nanoTime();
      if (remaining <= 0) throw new TimeoutException();
      return task.get(remaining, TimeUnit.NANOSECONDS);
    } catch (TimeoutException timeout) {
      task.cancel(true);
      workers.purge();
      throw new ProviderFailure(ProviderFailure.Kind.TIMEOUT);
    } catch (InterruptedException interrupted) {
      task.cancel(true);
      workers.purge();
      Thread.currentThread().interrupt();
      throw new ProviderFailure(ProviderFailure.Kind.INTERRUPTED);
    } catch (CancellationException canceled) {
      throw new ProviderFailure(ProviderFailure.Kind.INTERRUPTED);
    } catch (ExecutionException failed) {
      if (failed.getCause() instanceof ProviderFailure known) throw known;
      throw new ProviderFailure(ProviderFailure.Kind.ERROR);
    }
  }

  @PreDestroy
  public void shutdown() {
    for (Runnable waiting : workers.shutdownNow()) {
      if (waiting instanceof Future<?> task) task.cancel(false);
    }
  }
}
