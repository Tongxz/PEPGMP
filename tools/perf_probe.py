import json
import threading
import time
from typing import Dict, List, Tuple

try:
    import httpx  # type: ignore

    _USE_HTTPX = True
except Exception:
    _USE_HTTPX = False
    try:
        import requests  # type: ignore
    except Exception:
        requests = None  # type: ignore
        import urllib.request  # type: ignore


def _do_get(url: str, timeout: float = 5.0) -> Tuple[int, int]:
    t0 = time.perf_counter_ns()
    try:
        if _USE_HTTPX:
            r = httpx.get(url, timeout=timeout)
            code = r.status_code
        elif requests is not None:  # type: ignore
            r = requests.get(url, timeout=timeout)  # type: ignore
            code = r.status_code  # type: ignore
        else:
            with urllib.request.urlopen(url, timeout=timeout) as r:  # type: ignore
                code = r.getcode()
    except Exception:
        code = 599
    t1 = time.perf_counter_ns()
    return code, int((t1 - t0) / 1_000_000)  # ms


def run_probe(name: str, url: str, duration_s: int = 5, concurrency: int = 8) -> Dict:
    lat_ms: List[int] = []
    codes: List[int] = []
    stop_at = time.time() + duration_s

    def worker() -> None:
        while time.time() < stop_at:
            code, ms = _do_get(url)
            codes.append(code)
            lat_ms.append(ms)

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(concurrency)]
    t0 = time.time()
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    t1 = time.time()

    total = len(lat_ms)
    ok = sum(1 for c in codes if 200 <= c < 300)
    err = total - ok
    qps = total / max(1e-9, (t1 - t0))
    lat_sorted = sorted(lat_ms) if lat_ms else [0]

    def pct(p: float) -> float:
        if not lat_sorted:
            return 0.0
        k = min(len(lat_sorted) - 1, int(round(p * (len(lat_sorted) - 1))))
        return float(lat_sorted[k])

    return {
        "name": name,
        "url": url,
        "samples": total,
        "ok": ok,
        "errors": err,
        "qps": round(qps, 2),
        "latency_ms": {
            "p50": pct(0.50),
            "p95": pct(0.95),
            "p99": pct(0.99),
            "max": float(max(lat_sorted) if lat_sorted else 0.0),
        },
        "http_codes": {
            "2xx": ok,
            "others": err,
        },
    }


def main() -> None:
    base = "http://127.0.0.1:8000"
    targets = [
        ("summary", f"{base}/api/v1/statistics/summary?minutes=60&limit=1000"),
        (
            "violations",
            f"{base}/api/v1/records/violations?camera_id=cam0&limit=5&offset=0",
        ),
        ("camera_stats", f"{base}/api/v1/records/statistics/cam0?period=7d"),
    ]

    out: List[Dict] = []
    for name, url in targets:
        out.append(run_probe(name, url, duration_s=5, concurrency=8))

    print(json.dumps({"results": out}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
