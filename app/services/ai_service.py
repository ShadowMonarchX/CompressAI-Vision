from app.core.image_compressor import ImageCompressor
from app.core.config import settings
from app.core.feature_extraction import ImageFeatureExtractor, ImageFeatures
from app.core.parameter_predictor import CompressionParams, HeuristicPredictor
from app.core.quality_evaluator import QualityEvaluator

class AIService:
    """Orchestration boundary for extraction, prediction, compression and evaluation."""
    def __init__(self):
        self.extractor = ImageFeatureExtractor()
        self.predictor = HeuristicPredictor()
        self.compressor = ImageCompressor()
        self.evaluator = QualityEvaluator()

    async def compress_image(self, source, output):
        params = self.predictor.predict(self.extractor.extract(source))
        quality, score = params.quality, {"ssim": 0.0, "psnr": 0.0}
        for iteration in range(1, settings.max_iterations + 1):
            await self.compressor.compress(source, output, quality)
            score = self.evaluator.evaluate(source, output)
            if score['ssim'] >= self.evaluator.ssim_threshold or quality >= 98: break
            quality = min(98, quality + 8)
        return score, {'codec': params.codec, 'quality': quality, 'reason': params.reason}, iteration
    async def compare_image(self, source, ai_output, baseline_output):
        ai_result = await self.compress_image(source, ai_output)
        await self.compressor.compress(source, baseline_output, 75)
        baseline_score = self.evaluator.evaluate(source, baseline_output)
        return ai_result, (baseline_score, {'codec': 'JPEG', 'quality': 75, 'reason': 'fixed comparison baseline'}, 1)

class _FixedPredictor:
    def predict(self, features: ImageFeatures) -> CompressionParams:
        return CompressionParams(codec="JPEG", quality=75, reason="fixed comparison baseline")
