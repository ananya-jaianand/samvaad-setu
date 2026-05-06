"""
Per-stage latency tracking for the Samvaad-Setu voice pipeline.

Usage (anywhere in the codebase):
    from middleware.latency import track

    async with track("asr"):
        result = await asr.transcribe(...)

GET /health/latency exposes rolling p50/p95 per stage.
"""
import time
import statistics
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import AsyncIterator

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Rolling buffer — last 200 measurements per stage.
# 200 samples at ~1.5s/call ≈ 5 minutes of history.
_BUFFER_SIZE = 200

_stage_samples: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=_BUFFER_SIZE))


def record_stage(stage: str, duration_ms: float) -> None:
    """Record a single latency measurement for the given stage."""
    _stage_samples[stage].append(duration_ms)


@asynccontextmanager
async def track(stage: str) -> AsyncIterator[None]:
    """Async context manager that times a pipeline stage and records it."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        record_stage(stage, elapsed_ms)


def _percentile(data: list[float], pct: float) -> float:
    """Compute a percentile from a sorted list. pct in [0, 100]."""
    if not data:
        return 0.0
    if len(data) == 1:
        return data[0]
    # statistics.quantiles requires n >= 1 cuts; use linear interpolation
    n = len(data)
    idx = (pct / 100.0) * (n - 1)
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    frac = idx - lo
    return data[lo] + frac * (data[hi] - data[lo])


def get_stats() -> dict[str, dict]:
    """
    Return p50 and p95 latency (ms) for every tracked stage.
    Stages with no data are omitted.
    """
    result: dict[str, dict] = {}
    for stage, buf in _stage_samples.items():
        if not buf:
            continue
        samples = sorted(buf)
        result[stage] = {
            "p50_ms": round(_percentile(samples, 50), 2),
            "p95_ms": round(_percentile(samples, 95), 2),
            "min_ms": round(samples[0], 2),
            "max_ms": round(samples[-1], 2),
            "samples": len(samples),
        }
    return result


def clear_stats() -> None:
    """Reset all buffers — useful in tests."""
    _stage_samples.clear()


class LatencyMiddleware(BaseHTTPMiddleware):
    """
    FastAPI/Starlette middleware that records overall HTTP request latency
    under the stage name `http:{method}:{path_template}`.

    This complements the per-pipeline-stage tracking above; together they
    give end-to-end visibility without needing an external APM tool.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Use the matched route path (e.g. /sessions/{session_id}) not the actual URL,
        # so metrics aggregate sensibly across many sessions.
        route = request.scope.get("route")
        path = route.path if route else request.url.path
        stage = f"http:{request.method.upper()}:{path}"
        record_stage(stage, elapsed_ms)

        return response
