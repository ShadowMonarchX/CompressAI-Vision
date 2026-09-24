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
    def predict(self, features: Any) -> CompressionParams: ...

class HeuristicPredictor(BaseParameterPredictor):
    def predict(self, features: ImageFeatures | VideoFeatures) -> CompressionParams:
        if isinstance(features, VideoFeatures): return CompressionParams("libx264", reason="video baseline")
        quality = max(55, min(92, round(58 + (features.edge_density * 100 + features.entropy * 3) * .18)))
        return CompressionParams("JPEG", quality=quality, reason="entropy/edge-detail heuristic")
