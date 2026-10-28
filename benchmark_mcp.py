"""기존 로컬 서버의 실제 HTTP MCP 호출을 측정한다. 실행 위치: 저장소 루트.

서버 및 Bridge는 별도 터미널에서 실행한다. 모의 응답만 대상으로 하며 GPT API는 호출하지 않는다.
연결 초기화/워밍업을 측정 구간에서 제외한다. 프로덕션 분산 부하 테스트는 아니다.
"""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import statistics
import time

from vehicle_mcp.client import connect


def latency_summary(values):
    ordered = sorted(values)
    if not ordered:
        return None
    def percentile(p):
        return round(ordered[max(0, math.ceil(p * len(ordered)) - 1)], 3)
    return {
        "count": len(ordered), "mean": round(statistics.mean(ordered), 3),
        "p50": percentile(.50), "p95": percentile(.95), "p99": percentile(.99),
        "max": round(ordered[-1], 3),
    }


async def benchmark(args):
    started_at = datetime.now(timezone.utc).isoformat()
    samples = []
    initializations = []
    barrier = asyncio.Barrier(args.concurrency)
    window_start = None
    window_end = None

    def check(result):
        data = result.structuredContent or {}
        if result.isError:
            return "mcp_error"
        if data.get("status") != "ok":
            return str(data.get("status", "missing_status"))
        if data.get("source") != args.expected_source:
            return "wrong_source"
        # 기존 mock/mock_bridge의 고정 계약. 실차나 값을 바꾼 시뮬레이터에는 사용하지 않는다.
        if data.get("remaining_distance_m") != 12300 or data.get("remaining_duration_s") != 1080:
            return "wrong_values"
        return "ok"

    async def worker(index):
        nonlocal window_start, window_end
        started = time.perf_counter()
        async with connect() as session:
            initializations.append((time.perf_counter() - started) * 1000)
            tools = (await session.list_tools()).tools
            if [t.name for t in tools] != ["get_navigation_info"]:
                raise RuntimeError("Unexpected tool list")
            warmup_status = check(await session.call_tool("get_navigation_info", {}))
            if warmup_status != "ok":
                raise RuntimeError(f"Warmup failed: {warmup_status}; check server mode/Bridge")
            # 모든 클라이언트의 초기화와 워밍업이 완료된 뒤 부하를 시작한다.
            await barrier.wait()
            if window_start is None:
                window_start = time.perf_counter()
            for request_index in range(index, args.requests, args.concurrency):
                call_start = time.perf_counter()
                try:
                    status = check(await session.call_tool("get_navigation_info", {}))
                except Exception as error:
                    # 인증정보나 SDK 응답 본문은 보고서에 저장하지 않는다.
                    status = "exception:" + type(error).__name__
                finished = time.perf_counter()
                window_end = finished
                samples.append({
                    "request": request_index, "worker": index, "status": status,
                    "latency_ms": round((finished - call_start) * 1000, 3),
                })

    # 초기화 실패 시 대기 중인 다른 워커도 취소해 무한 대기를 방지한다.
    async with asyncio.TaskGroup() as group:
        for index in range(args.concurrency):
            group.create_task(worker(index))
    elapsed = window_end - window_start
    counts = Counter(sample["status"] for sample in samples)
    return {
        "started_at_utc": started_at,
        "label": args.label, "expected_source": args.expected_source,
        "python": platform.python_version(), "os": platform.system(), "mcp": version("mcp"),
        "requests": len(samples), "concurrency": args.concurrency,
        "status_counts": dict(counts), "success_rate": counts["ok"] / len(samples),
        "elapsed_seconds": round(elapsed, 3),
        "completed_requests_per_second": round(len(samples) / elapsed, 3),
        "successful_requests_per_second": round(counts["ok"] / elapsed, 3),
        "session_initialization_ms": latency_summary(initializations),
        "all_call_latency_ms": latency_summary([s["latency_ms"] for s in samples]),
        "successful_call_latency_ms": latency_summary([s["latency_ms"] for s in samples if s["status"] == "ok"]),
        "method": "One initialized session per worker; one warmup call per worker excluded; closed-loop load.",
        "samples": sorted(samples, key=lambda s: s["request"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--expected-source", choices=["mock", "mock_bridge"], required=True)
    parser.add_argument("--label", default="local")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.concurrency <= 16 or args.requests < args.concurrency:
        parser.error("Use concurrency 1..16 and requests >= concurrency")
    if args.output.exists():
        parser.error("Output already exists; choose a new filename to preserve previous results")
    report = asyncio.run(benchmark(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != "samples"}, ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    raise SystemExit(0 if report["status_counts"] == {"ok": args.requests} else 1)


if __name__ == "__main__":
    main()
