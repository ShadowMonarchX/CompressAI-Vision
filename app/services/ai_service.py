import asyncio
from app.core.image_compressor import ImageCompressor
from app.core.config import settings
from app.core.feature_extraction import ImageFeatureExtractor, ImageFeatures
from app.core.parameter_predictor import CompressionParams, HeuristicPredictor
from app.core.quality_evaluator import QualityEvaluator
from app.core.exceptions import (CompressionFailedError, QualityThresholdUnreachableError,
    FFmpegNotAvailableError, FFmpegTimeoutError)
import shutil

class AIService:
    """Orchestration boundary for extraction, prediction, compression and evaluation."""
    def __init__(self):
        self.extractor = ImageFeatureExtractor()
        self.predictor = HeuristicPredictor()
        self.compressor = ImageCompressor()
        self.evaluator = QualityEvaluator()

    async def compress_image(self, source, output):
        try: params = self.predictor.predict(self.extractor.extract(source))
        except Exception as exc: raise CompressionFailedError("Feature extraction or parameter prediction failed", stage="feature_extraction") from exc
        quality, score = params.quality, {"ssim": 0.0, "psnr": 0.0}
        for iteration in range(1, settings.max_iterations + 1):
            try:
                await self.compressor.compress(source, output, quality)
                score = self.evaluator.evaluate(source, output)
            except Exception as exc: raise CompressionFailedError("Compression or quality evaluation failed", stage="compression") from exc
            if score['ssim'] >= self.evaluator.ssim_threshold or quality >= 98: break
            quality = min(98, quality + 8)
        if score['ssim'] < self.evaluator.ssim_threshold and quality >= 98:
            raise QualityThresholdUnreachableError("Quality threshold could not be reached", best_score=score)
        return score, {'codec': params.codec, 'quality': quality, 'reason': params.reason}, iteration
    async def compare_image(self, source, ai_output, baseline_output):
        ai_result = await self.compress_image(source, ai_output)
        await self.compressor.compress(source, baseline_output, 75)
        baseline_score = self.evaluator.evaluate(source, baseline_output)
        return ai_result, (baseline_score, {'codec': 'JPEG', 'quality': 75, 'reason': 'fixed comparison baseline'}, 1)

    async def compress_video(self, source, output):
        """Transcode video with FFmpeg without sending it through Pillow."""
        if not shutil.which(settings.ffmpeg_binary): raise FFmpegNotAvailableError("ffmpeg is unavailable")
        output.parent.mkdir(parents=True, exist_ok=True)
        process = await asyncio.create_subprocess_exec(
            settings.ffmpeg_binary, '-y', '-i', str(source), '-c:v', 'libx264',
            '-preset', 'medium', '-crf', '28', '-c:a', 'aac', str(output),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try: _, stderr = await asyncio.wait_for(process.communicate(), timeout=settings.ffmpeg_timeout)
        except asyncio.TimeoutError as exc:
            process.kill(); await process.wait(); raise FFmpegTimeoutError("FFmpeg timed out") from exc
        if process.returncode != 0:
            detail = stderr.decode(errors='replace').strip().splitlines()[-1:]
            raise CompressionFailedError("FFmpeg compression failed", stderr_tail=' '.join(detail))
        return {'codec': 'libx264', 'quality': 28, 'reason': 'FFmpeg video transcode'}

class _FixedPredictor:
    def predict(self, features: ImageFeatures) -> CompressionParams:
        return CompressionParams(codec="JPEG", quality=75, reason="fixed comparison baseline")
