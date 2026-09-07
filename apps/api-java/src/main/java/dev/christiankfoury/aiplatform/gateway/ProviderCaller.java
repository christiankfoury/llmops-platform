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
    for (int attempt = 1; attempt <= settings.maxAttempts(); attempt++) {
      try {
        return attempt(context, input, attempt);
      } catch (ProviderFailure failure) {
        if (!failure.kind().retryable() || attempt == settings.maxAttempts()) throw failure;
        try {
          Thread.sleep(settings.retryBackoff());
        } catch (InterruptedException interrupted) {
          Thread.currentThread().interrupt();
          throw new ProviderFailure(ProviderFailure.Kind.INTERRUPTED);
        }
      }
    }
    throw new ProviderFailure(ProviderFailure.Kind.ERROR);
  }

  private CompletionProvider.Result attempt(GatewayContext context, String input, int attempt) {
    java.util.concurrent.Future<CompletionProvider.Result> task;
    try {
      task = workers.submit(() -> provider.complete(context, input, attempt));
    } catch (RejectedExecutionException busy) {
      throw new ProviderFailure(ProviderFailure.Kind.BUSY);
    }
    try {
      return task.get(settings.timeout().toMillis(), TimeUnit.MILLISECONDS);
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
