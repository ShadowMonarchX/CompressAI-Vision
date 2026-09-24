"""Image compression orchestration."""
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from PIL import Image
from .feature_extraction import ImageFeatureExtractor
from .parameter_predictor import HeuristicPredictor
from .quality_evaluator import QualityEvaluator

class BaseCompressor(ABC):
    @abstractmethod
    async def compress(self, source: Path, output: Path): ...
    @abstractmethod
    def estimate_params(self, source: Path): ...
    @staticmethod
    def validate_output(output: Path) -> bool:
        return output.is_file() and output.stat().st_size > 0

class ImageCompressor(BaseCompressor):
    def __init__(self, predictor=None, evaluator=None, max_iterations: int = 3) -> None:
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        self.predictor = predictor or HeuristicPredictor()
        self.evaluator = evaluator or QualityEvaluator()
        self.max_iterations = max_iterations

    def estimate_params(self, source: Path):
        return self.predictor.predict(ImageFeatureExtractor().extract(source))

    async def compress(self, source: Path, output: Path):
        return await asyncio.to_thread(self._compress, source, output)

    def _compress(self, source: Path, output: Path):
        output.parent.mkdir(parents=True, exist_ok=True)
        params = self.estimate_params(source)
        quality = params.quality
        score = {"ssim": 0.0, "psnr": 0.0}
        for iteration in range(1, self.max_iterations + 1):
            with Image.open(source) as image:
                image.convert("RGB").save(output, "JPEG", quality=quality, optimize=True)
            score = self.evaluator.evaluate(source, output)
            if score["ssim"] >= self.evaluator.ssim_threshold or quality >= 98:
                break
            quality = min(98, quality + 8)
        return score, {"codec": params.codec, "quality": quality, "reason": params.reason}, iteration

