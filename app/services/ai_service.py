import asyncio
import logging
import re
import shutil
import time

from app.core.config import settings
from app.core.exceptions import (
    CompressionFailedError,
    FFmpegNotAvailableError,
    FFmpegTimeoutError,
    QualityThresholdUnreachableError,
)
from app.core.feature_extraction import ImageFeatureExtractor, ImageFeatures
from app.core.image_compressor import ImageCompressor
from app.core.parameter_predictor import CompressionParams, HeuristicPredictor, quality_target_to_params
from app.core.quality_evaluator import QualityEvaluator

logger = logging.getLogger(__name__)


class AIService:
    """Orchestration boundary for extraction, prediction, compression and evaluation."""

    def __init__(self) -> None:
        self.extractor = ImageFeatureExtractor()
        self.predictor = HeuristicPredictor()
        self.compressor = ImageCompressor()
        self.evaluator = QualityEvaluator()

    async def compress_image(self, source, output, quality_target: int = 85) -> tuple:
        target = quality_target_to_params(quality_target)
        evaluator = QualityEvaluator(ssim_threshold=target.ssim_threshold)
        try:
            params = self.predictor.predict(self.extractor.extract(source))
        except Exception as exc:
            raise CompressionFailedError(
                "Feature extraction or parameter prediction failed", stage="feature_extraction"
            ) from exc
        quality, score = target.params.quality, {"ssim": 0.0, "psnr": 0.0}
        for iteration in range(1, settings.max_iterations + 1):
            try:
                await self.compressor.compress(source, output, quality)
                score = evaluator.evaluate(source, output)
            except Exception as exc:
                raise CompressionFailedError(
                    "Compression or quality evaluation failed", stage="compression"
                ) from exc
            if score["ssim"] >= evaluator.ssim_threshold or quality >= 98:
                break
            quality = min(98, quality + 8)
        if score["ssim"] < evaluator.ssim_threshold and quality >= 98:
            raise QualityThresholdUnreachableError("Quality threshold could not be reached", best_score=score)

        return score, {"codec": params.codec, "quality": quality, "reason": target.params.reason}, iteration

    async def compare_image(self, source, ai_output, baseline_output, quality_target: int = 85):
        ai_result = await self.compress_image(source, ai_output, quality_target)
        await self.compressor.compress(source, baseline_output, 75)
        baseline_score = self.evaluator.evaluate(source, baseline_output)
        return ai_result, (
            baseline_score,
            {"codec": "JPEG", "quality": 75, "reason": "fixed comparison baseline"},
            1,
        )

    async def compress_video(self, source, output, quality_target: int = 85):
        """Transcode video and verify the result with one full FFmpeg pass."""
        if not shutil.which(settings.ffmpeg_binary):
            raise FFmpegNotAvailableError("ffmpeg is unavailable")
        output.parent.mkdir(parents=True, exist_ok=True)
        crf = quality_target_to_params(quality_target).params.crf
        started = time.perf_counter()
        logger.info("video_compression_started source=%s encoder=%s preset=%s crf=%s", source, settings.video_encoder, settings.video_encode_preset, crf)
        process = await asyncio.create_subprocess_exec(
            settings.ffmpeg_binary,
            "-y",
            "-i",
            str(source),
            "-c:v",
            settings.video_encoder,
            "-preset",
            settings.video_encode_preset,
            "-crf",
            str(crf),
            "-c:a",
            "aac",
            str(output),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try: _, stderr = await asyncio.wait_for(process.communicate(), timeout=settings.ffmpeg_timeout)
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.wait()
            raise FFmpegTimeoutError("FFmpeg timed out") from exc
        if process.returncode != 0:
            detail = stderr.decode(errors="replace").strip().splitlines()[-1:]
            raise CompressionFailedError("FFmpeg compression failed", stderr_tail=" ".join(detail))
        duration = round(time.perf_counter() - started, 3)
        verify_started = time.perf_counter()
        verify = await self._evaluate_video(source, output)
        verify_duration = round(time.perf_counter() - verify_started, 3)
        threshold = quality_target_to_params(quality_target).ssim_threshold
        logger.info(
            "video_compression_finished source=%s stage=full_encode duration_seconds=%s "
            "verification_seconds=%s ssim=%s psnr=%s iterations=1",
            source, duration, verify_duration, verify["ssim"], verify["psnr"],
        )
        return {
            "codec": settings.video_encoder, "preset": settings.video_encode_preset,
            "crf": crf, "duration_seconds": duration,
            "verification_duration_seconds": verify_duration,
            "verified_ssim": verify["ssim"], "verified_psnr": verify["psnr"],
            "quality_target": quality_target, "quality_target_met": verify["ssim"] >= threshold,
            "reason": "FFmpeg video transcode with single-pass verification",
        }

    async def _evaluate_video(self, source, output) -> dict[str, float]:
        """Compare decoded video streams using FFmpeg's SSIM and PSNR filters."""
        process = await asyncio.create_subprocess_exec(
            settings.ffmpeg_binary, "-hide_banner", "-i", str(source), "-i", str(output),
            "-lavfi", "[0:v][1:v]ssim;[0:v][1:v]psnr", "-f", "null", "-",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await asyncio.wait_for(process.communicate(), timeout=settings.ffmpeg_timeout)
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.wait()
            raise FFmpegTimeoutError("FFmpeg quality verification timed out") from exc
        if process.returncode != 0:
            raise CompressionFailedError("FFmpeg quality verification failed", stderr_tail=stderr.decode(errors="replace")[-500:])
        text = stderr.decode(errors="replace")
        ssim = re.findall(r"SSIM.*?All:([0-9.]+)", text)
        psnr = re.findall(r"PSNR.*?average:([0-9.]+)", text)
        if not ssim or not psnr:
            raise CompressionFailedError("FFmpeg quality verification returned no metrics")
        return {"ssim": float(ssim[-1]), "psnr": float(psnr[-1])}

class _FixedPredictor:
    def predict(self, features: ImageFeatures) -> CompressionParams:
        return CompressionParams(codec="JPEG", quality=75, reason="fixed comparison baseline")
