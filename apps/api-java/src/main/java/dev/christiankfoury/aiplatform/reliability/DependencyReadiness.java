package dev.christiankfoury.aiplatform.reliability;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import javax.sql.DataSource;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.stereotype.Component;

/** One bounded checker per instance. Probes never acquire database connections or enqueue work. */
@Component
public class DependencyReadiness {
  private record Snapshot(boolean database, boolean redis, long checkedAt) {}

  private final DataSource database;
  private final RedisConnectionFactory redis;
  private final DrainState drain;
  private final ScheduledExecutorService checker =
      Executors.newSingleThreadScheduledExecutor(
          Thread.ofPlatform().daemon(true).name("dependency-readiness").factory());
  private volatile Snapshot snapshot = new Snapshot(false, false, 0);

  public DependencyReadiness(DataSource database, RedisConnectionFactory redis, DrainState drain) {
    this.database = database;
    this.redis = redis;
    this.drain = drain;
  }

  @PostConstruct
  void start() {
    refresh();
    checker.scheduleWithFixedDelay(this::refresh, 1, 1, TimeUnit.SECONDS);
  }

  public boolean ready() {
    Snapshot current = snapshot;
    return !drain.draining()
        && current.database
        && current.redis
        && System.nanoTime() - current.checkedAt < TimeUnit.SECONDS.toNanos(3);
  }

  public synchronized void refresh() {
    boolean databaseReady = false;
    boolean redisReady = false;
    try (var connection = database.getConnection();
        var statement = connection.createStatement()) {
      statement.setQueryTimeout(1);
      try (var result = statement.executeQuery("SELECT 1")) {
        databaseReady = result.next() && result.getInt(1) == 1;
      }
    } catch (Exception failure) {
      /* Readiness reveals no credentials or diagnostics. */
    }
    try (var connection = redis.getConnection()) {
      redisReady = "PONG".equals(connection.ping());
    } catch (Exception failure) {
      /* The next bounded check can recover without restarting the process. */
    }
    snapshot = new Snapshot(databaseReady, redisReady, System.nanoTime());
  }

  @PreDestroy
  void close() {
    checker.shutdownNow();
  }
}
