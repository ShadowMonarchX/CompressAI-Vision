from abc import ABC, abstractmethod
from pathlib import Path
from PIL import Image
from .feature_extraction import ImageFeatureExtractor
from .parameter_predictor import BaseParameterPredictor, HeuristicPredictor
from .quality_evaluator import QualityEvaluator

class BaseCompressor(ABC):
    @abstractmethod
    async def compress(self, source: Path, output: Path): ...
    @abstractmethod
    def estimate_params(self, source: Path): ...
    def validate_output(self, output: Path) -> bool: return output.exists() and output.stat().st_size > 0

class ImageCompressor(BaseCompressor):
    def __init__(self, predictor=None, evaluator=None, max_iterations=3):
        self.predictor = predictor or HeuristicPredictor(); self.evaluator = evaluator or QualityEvaluator(); self.max_iterations = max_iterations
    def estimate_params(self, source): return self.predictor.predict(ImageFeatureExtractor().extract(source))
    async def compress(self, source, output):
        import asyncio
        return await asyncio.to_thread(self._compress, source, output)
    def _compress(self, source, output):
        params = self.estimate_params(source); quality = params.quality
        for iteration in range(1, self.max_iterations + 1):
            with Image.open(source) as im: im.convert("RGB").save(output, "JPEG", quality=quality, optimize=True)
            score = self.evaluator.evaluate(source, output)
            if score["ssim"] >= self.evaluator.ssim_threshold or quality >= 98: break
            quality = min(98, quality + 8)
        return score, {"codec": params.codec, "quality": quality, "reason": params.reason}, iteration
