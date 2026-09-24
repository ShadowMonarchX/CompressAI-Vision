"""Compression parameter prediction strategies."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from .feature_extraction import ImageFeatures, VideoFeatures

@dataclass(frozen=True)
class CompressionParams:
    codec: str
    quality: int = 80
    preset: str = "medium"
    crf: int = 28
    reason: str = ""

class BaseParameterPredictor(ABC):
    @abstractmethod
    def predict(self, features: Any) -> CompressionParams:
        """Choose codec parameters for extracted media features."""

class HeuristicPredictor(BaseParameterPredictor):
    def predict(self, features: ImageFeatures | VideoFeatures) -> CompressionParams:
        if isinstance(features, VideoFeatures):
            return CompressionParams("libx264", reason="video baseline")
        if not isinstance(features, ImageFeatures):
            raise TypeError("HeuristicPredictor expects image or video features")
        quality = round(58 + (features.edge_density * 100 + features.entropy * 3) * 0.18)
        quality = max(55, min(92, quality))
        return CompressionParams("JPEG", quality=quality, reason="entropy/edge-detail heuristic")

