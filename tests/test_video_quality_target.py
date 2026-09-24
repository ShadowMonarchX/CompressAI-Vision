from app.core.parameter_predictor import quality_target_to_params
import asyncio
import pytest
from app.services.ai_service import AIService


def test_video_quality_target_changes_crf_directionally():
    low = quality_target_to_params(10)
    high = quality_target_to_params(90)

    assert low.params.crf == 33
    assert high.params.crf == 15
    assert low.params.crf > high.params.crf


def test_video_mapping_exposes_verification_contract():
    target = quality_target_to_params(90)
    assert target.ssim_threshold == pytest.approx(0.941)


def test_video_request_passes_target_crf_and_reports_verified_quality(monkeypatch, tmp_path):
    """Regression coverage for the video path, not only the mapping helper."""
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fixture")
    output = tmp_path / "output.mp4"
    seen = []

    class Process:
        returncode = 0

        async def communicate(self):
            return b"", b""

        async def wait(self):
            return None

    async def fake_exec(*args, **kwargs):
        seen.append(args)
        output.write_bytes(b"encoded")
        return Process()

    async def fake_evaluate(self, original, compressed):
        return {"ssim": 0.96, "psnr": 42.0}

    monkeypatch.setattr("app.services.ai_service.shutil.which", lambda _: "/usr/bin/ffmpeg")
    monkeypatch.setattr("app.services.ai_service.asyncio.create_subprocess_exec", fake_exec)
    monkeypatch.setattr(AIService, "_evaluate_video", fake_evaluate)

    async def exercise():
        low = await AIService().compress_video(source, output, quality_target=10)
        high = await AIService().compress_video(source, output, quality_target=90)
        return low, high

    low, high = asyncio.run(exercise())

    assert low["crf"] > high["crf"]
    assert low["quality_target"] == 10 and high["quality_target"] == 90
    assert low["verified_ssim"] == high["verified_ssim"] == 0.96
    assert seen[0][seen[0].index("-crf") + 1] == "33"
    assert seen[1][seen[1].index("-crf") + 1] == "15"
