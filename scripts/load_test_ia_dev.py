#!/usr/bin/env python3
import argparse
import json
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def _request_json(method: str, url: str, payload: dict | None, headers: dict) -> tuple[int, dict, int]:
    body = None
    req_headers = {"Content-Type": "application/json", **headers}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url=url, method=method.upper(), data=body, headers=req_headers)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return resp.status, json.loads(raw or "{}"), elapsed_ms
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        try:
            data = json.loads(raw or "{}")
        except Exception:
            data = {"raw": raw}
        return int(exc.code), data, elapsed_ms


def main():
    parser = argparse.ArgumentParser(description="Carga basica para IA DEV governance")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="URL base del backend")
    parser.add_argument("--token", default="", help="Bearer token opcional")
    parser.add_argument("--workers", type=int, default=8, help="Hilos concurrentes")
    parser.add_argument("--requests", type=int, default=40, help="Numero de requests a enviar")
    parser.add_argument(
        "--endpoint",
        default="/ia-dev/health/",
        choices=["/ia-dev/health/", "/ia-dev/observability/summary/"],
        help="Endpoint a estresar",
    )
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    endpoint = args.endpoint
    headers = {}
    if args.token.strip():
        headers["Authorization"] = f"Bearer {args.token.strip()}"

    def _worker(i: int):
        url = f"{base}{endpoint}"
        if endpoint == "/ia-dev/observability/summary/":
            query = urllib.parse.urlencode({"window_seconds": 3600, "limit": 1000})
            url = f"{url}?{query}"
        return _request_json("GET", url, payload=None, headers=headers)

    codes: list[int] = []
    latencies: list[int] = []
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = [executor.submit(_worker, i) for i in range(max(1, args.requests))]
        for fut in as_completed(futures):
            code, _data, elapsed_ms = fut.result()
            codes.append(code)
            latencies.append(elapsed_ms)

    total_ms = int((time.perf_counter() - started) * 1000)
    ok_count = sum(1 for c in codes if 200 <= c < 300)
    fail_count = len(codes) - ok_count
    p95 = int(sorted(latencies)[min(len(latencies) - 1, int(len(latencies) * 0.95))]) if latencies else 0

    print("=== IA DEV Load Test Summary ===")
    print(f"endpoint: {endpoint}")
    print(f"requests: {len(codes)}")
    print(f"ok: {ok_count}")
    print(f"fail: {fail_count}")
    print(f"total_ms: {total_ms}")
    if latencies:
        print(f"avg_ms: {int(statistics.mean(latencies))}")
        print(f"p95_ms: {p95}")
        print(f"max_ms: {max(latencies)}")
    print(f"status_codes: {dict(sorted({c: codes.count(c) for c in set(codes)}.items()))}")


if __name__ == "__main__":
    main()
