from app.core.image_compressor import ImageCompressor
from app.core.config import settings
from app.core.feature_extraction import ImageFeatures
from app.core.parameter_predictor import CompressionParams
from app.core.quality_evaluator import QualityEvaluator

class AIService:
    """Orchestration boundary for extraction, prediction, compression and evaluation."""
    def __init__(self): self.compressor = ImageCompressor(max_iterations=settings.max_iterations)
    async def compress_image(self, source, output): return await self.compressor.compress(source, output)
    async def compare_image(self, source, ai_output, baseline_output):
        ai_result = await self.compressor.compress(source, ai_output)
        baseline = ImageCompressor(predictor=_FixedPredictor(), evaluator=QualityEvaluator(), max_iterations=1)
        return ai_result, await baseline.compress(source, baseline_output)

class _FixedPredictor:
    def predict(self, features: ImageFeatures) -> CompressionParams:
        return CompressionParams(codec="JPEG", quality=75, reason="fixed comparison baseline")
