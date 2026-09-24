from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from PIL import Image

@dataclass(frozen=True)
class ImageFeatures:
    entropy: float
    edge_density: float
    variance: float

@dataclass(frozen=True)
class VideoFeatures:
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0

class BaseFeatureExtractor(ABC):
    @abstractmethod
    def extract(self, path: Path): ...

class ImageFeatureExtractor(BaseFeatureExtractor):
    def extract(self, path: Path) -> ImageFeatures:
        with Image.open(path) as im:
            a = np.asarray(im.convert("L").resize((min(512, im.width), min(512, im.height))), dtype=np.float32)
        hist = np.histogram(a, bins=256, range=(0, 256), density=True)[0]
        entropy = float(-(hist[hist > 0] * np.log2(hist[hist > 0])).sum())
        gx, gy = np.gradient(a)
        return ImageFeatures(entropy, float(np.mean(np.hypot(gx, gy) > 18)), float(np.var(a)))

class VideoFeatureExtractor(BaseFeatureExtractor):
    def extract(self, path: Path) -> VideoFeatures:
        return VideoFeatures()
