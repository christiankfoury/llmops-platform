from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Result:
    status_code: int
    latency_ms: int
    ok: bool


def _post_gateway(base_url: str, api_key: str, prompt_name: str, index: int) -> Result:
    started_at = time.perf_counter()
    body = json.dumps(
        {
            "prompt_name": prompt_name,
            "input": f"smoke load request {index}",
        }
    ).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}/v1/gateway/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            "X-Request-ID": f"smoke-load-{index}",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            status_code = response.status
            response.read()
    except HTTPError as exc:
        status_code = exc.code
    except URLError:
        status_code = 0

    latency_ms = max(1, int((time.perf_counter() - started_at) * 1000))
    return Result(status_code=status_code, latency_ms=latency_ms, ok=200 <= status_code < 300)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a small smoke load through the LLM gateway.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--api-key", default="local-dev-placeholder-key-not-a-secret")
    parser.add_argument("--prompt-name", default="default")
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    total_requests = max(1, args.requests)
    concurrency = max(1, args.concurrency)
    results: list[Result] = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(_post_gateway, args.base_url, args.api_key, args.prompt_name, index)
            for index in range(1, total_requests + 1)
        ]
        for future in as_completed(futures):
            results.append(future.result())

    ok_count = sum(1 for result in results if result.ok)
    latencies = [result.latency_ms for result in results]
    status_counts: dict[int, int] = {}
    for result in results:
        status_counts[result.status_code] = status_counts.get(result.status_code, 0) + 1

    print(f"requests={total_requests}")
    print(f"successful={ok_count}")
    print(f"failed={total_requests - ok_count}")
    print(f"status_counts={dict(sorted(status_counts.items()))}")
    print(f"latency_ms_min={min(latencies)}")
    print(f"latency_ms_avg={round(statistics.mean(latencies), 2)}")
    print(f"latency_ms_max={max(latencies)}")

    return 0 if ok_count == total_requests else 1


if __name__ == "__main__":
    raise SystemExit(main())
