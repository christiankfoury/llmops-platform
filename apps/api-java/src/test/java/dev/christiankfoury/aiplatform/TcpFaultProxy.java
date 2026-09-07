package dev.christiankfoury.aiplatform;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/** Test-only network fault injection; closes only connections accepted by this loopback proxy. */
final class TcpFaultProxy implements AutoCloseable {
  private final ServerSocket listener;
  private final String targetHost;
  private final int targetPort;
  private final AtomicBoolean blocked = new AtomicBoolean();
  private final Set<Socket> connections = ConcurrentHashMap.newKeySet();
  private final java.util.concurrent.ExecutorService transfers =
      Executors.newVirtualThreadPerTaskExecutor();

  TcpFaultProxy(String host, int port) {
    targetHost = host;
    targetPort = port;
    try {
      listener = new ServerSocket();
      listener.bind(new InetSocketAddress("127.0.0.1", 0));
      Thread.ofPlatform().daemon(true).name("fixture-fault-proxy").start(this::accept);
      Runtime.getRuntime().addShutdownHook(new Thread(this::close));
    } catch (IOException failure) {
      throw new IllegalStateException(failure);
    }
  }

  int port() {
    return listener.getLocalPort();
  }

  void disconnect() {
    blocked.set(true);
    connections.forEach(TcpFaultProxy::closeSocket);
  }

  void recover() {
    blocked.set(false);
  }

  private void accept() {
    while (!listener.isClosed()) {
      try {
        Socket incoming = listener.accept();
        connections.add(incoming);
        if (blocked.get()) {
          closeSocket(incoming);
          connections.remove(incoming);
          continue;
        }
        Socket target = new Socket();
        connections.add(target);
        try {
          target.connect(new InetSocketAddress(targetHost, targetPort), 500);
          if (blocked.get()) {
            closeSocket(incoming);
            closeSocket(target);
            connections.remove(incoming);
            connections.remove(target);
            continue;
          }
          transfers.submit(() -> copy(incoming, target));
          transfers.submit(() -> copy(target, incoming));
        } catch (IOException failure) {
          closeSocket(incoming);
          closeSocket(target);
          connections.remove(incoming);
          connections.remove(target);
        }
      } catch (IOException failure) {
        if (!listener.isClosed()) throw new IllegalStateException(failure);
      }
    }
  }

  private void copy(Socket from, Socket to) {
    try {
      from.getInputStream().transferTo(to.getOutputStream());
    } catch (IOException expectedDuringFault) {
      /* Intentional connection loss. */
    } finally {
      closeSocket(from);
      closeSocket(to);
      connections.remove(from);
      connections.remove(to);
    }
  }

  private static void closeSocket(Socket socket) {
    try {
      socket.close();
    } catch (IOException ignored) {
      /* Already closed. */
    }
  }

  @Override
  public void close() {
    disconnect();
    try {
      listener.close();
    } catch (IOException ignored) {
      /* Already closed. */
    }
    transfers.shutdownNow();
  }
}
