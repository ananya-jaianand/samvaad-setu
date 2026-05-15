"""
Tests for middleware/latency.py — rolling buffer, percentile computation,
the track() context manager, and the /health/latency endpoint.
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pytest_asyncio
from middleware.latency import (
    record_stage,
    track,
    get_stats,
    clear_stats,
    _percentile,
)


@pytest.fixture(autouse=True)
def reset():
    """Ensure a clean buffer before every test."""
    clear_stats()
    yield
    clear_stats()


# ── _percentile helper ────────────────────────────────────────────────────────

class TestPercentile:
    def test_single_element(self):
        assert _percentile([42.0], 50) == 42.0
        assert _percentile([42.0], 95) == 42.0

    def test_empty_returns_zero(self):
        assert _percentile([], 50) == 0.0

    def test_p50_of_even_list(self):
        data = sorted([10.0, 20.0, 30.0, 40.0])
        p50 = _percentile(data, 50)
        assert 20.0 <= p50 <= 30.0

    def test_p95_of_100_elements(self):
        data = sorted(float(i) for i in range(1, 101))
        p95 = _percentile(data, 95)
        assert 94.0 <= p95 <= 96.0

    def test_p0_equals_min(self):
        data = sorted([5.0, 10.0, 15.0, 20.0])
        assert _percentile(data, 0) == pytest.approx(5.0)

    def test_p100_equals_max(self):
        data = sorted([5.0, 10.0, 15.0, 20.0])
        assert _percentile(data, 100) == pytest.approx(20.0)


# ── record_stage / get_stats ──────────────────────────────────────────────────

class TestRecordStage:
    def test_single_record_appears_in_stats(self):
        record_stage("asr", 250.0)
        stats = get_stats()
        assert "asr" in stats
        assert stats["asr"]["samples"] == 1
        assert stats["asr"]["p50_ms"] == pytest.approx(250.0)
        assert stats["asr"]["p95_ms"] == pytest.approx(250.0)

    def test_multiple_stages_tracked_independently(self):
        record_stage("asr", 300.0)
        record_stage("nlu", 450.0)
        record_stage("tts", 380.0)
        stats = get_stats()
        assert "asr" in stats
        assert "nlu" in stats
        assert "tts" in stats
        assert stats["asr"]["samples"] == 1
        assert stats["nlu"]["p50_ms"] == pytest.approx(450.0)

    def test_p50_and_p95_differ_with_enough_samples(self):
        # 10 at 100ms + 10 at 900ms → p50 ≈ 500ms, p95 ≈ 860ms
        for _ in range(10):
            record_stage("asr", 100.0)
        for _ in range(10):
            record_stage("asr", 900.0)
        stats = get_stats()
        assert stats["asr"]["p50_ms"] < stats["asr"]["p95_ms"]
        assert stats["asr"]["p95_ms"] > 800.0
        assert stats["asr"]["p50_ms"] < 600.0

    def test_buffer_caps_at_200(self):
        for i in range(250):
            record_stage("asr", float(i))
        stats = get_stats()
        assert stats["asr"]["samples"] == 200

    def test_empty_stage_not_in_stats(self):
        stats = get_stats()
        assert "asr" not in stats

    def test_min_max_reported(self):
        for v in [50.0, 100.0, 200.0, 400.0]:
            record_stage("nlu", v)
        stats = get_stats()
        assert stats["nlu"]["min_ms"] == pytest.approx(50.0)
        assert stats["nlu"]["max_ms"] == pytest.approx(400.0)


# ── track() context manager ───────────────────────────────────────────────────

class TestTrackContextManager:
    @pytest.mark.asyncio
    async def test_track_records_nonzero_duration(self):
        async with track("asr"):
            await asyncio.sleep(0.01)  # 10ms
        stats = get_stats()
        assert "asr" in stats
        assert stats["asr"]["p50_ms"] >= 5.0   # allow some clock slack

    @pytest.mark.asyncio
    async def test_track_records_even_on_exception(self):
        try:
            async with track("nlu"):
                raise ValueError("test error")
        except ValueError:
            pass
        stats = get_stats()
        assert "nlu" in stats
        assert stats["nlu"]["samples"] == 1

    @pytest.mark.asyncio
    async def test_multiple_tracks_accumulate(self):
        for _ in range(3):
            async with track("tts"):
                await asyncio.sleep(0.001)
        stats = get_stats()
        assert stats["tts"]["samples"] == 3


# ── /health/latency endpoint ──────────────────────────────────────────────────

class TestHealthLatencyEndpoint:
    @pytest_asyncio.fixture
    async def client(self):
        import httpx
        from main import app
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c

    @pytest.mark.asyncio
    async def test_endpoint_returns_200(self, client):
        resp = await client.get("/health/latency")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_endpoint_shape(self, client):
        resp = await client.get("/health/latency")
        body = resp.json()
        assert "stages" in body
        assert isinstance(body["stages"], dict)

    @pytest.mark.asyncio
    async def test_endpoint_reflects_recorded_stages(self, client):
        record_stage("asr", 300.0)
        record_stage("nlu", 500.0)

        resp = await client.get("/health/latency")
        stages = resp.json()["stages"]
        assert "asr" in stages
        assert "nlu" in stages
        assert stages["asr"]["samples"] == 1
        assert stages["asr"]["p50_ms"] == pytest.approx(300.0)

    @pytest.mark.asyncio
    async def test_endpoint_empty_when_no_data(self, client):
        resp = await client.get("/health/latency")
        body = resp.json()
        # HTTP routes may appear from the /health/latency call itself
        # (LatencyMiddleware records them), but pipeline stages should be absent
        pipeline_stages = {"asr", "nlu", "sentiment", "verification", "tts"}
        present = set(body["stages"].keys()) & pipeline_stages
        assert present == set()
