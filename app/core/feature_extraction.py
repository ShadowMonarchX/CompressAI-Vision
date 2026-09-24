"""Feature extraction used by compression parameter prediction."""
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
    def extract(self, path: Path):
        """Extract model features from a media file."""

class ImageFeatureExtractor(BaseFeatureExtractor):
    def extract(self, path: Path) -> ImageFeatures:
        with Image.open(path) as image:
            width = max(1, min(512, image.width))
            height = max(1, min(512, image.height))
            pixels = np.asarray(image.convert("L").resize((width, height)), dtype=np.float32)
        histogram = np.histogram(pixels, bins=256, range=(0, 256))[0]
        probabilities = histogram[histogram > 0] / pixels.size
        entropy = float(-(probabilities * np.log2(probabilities)).sum())
        gradient_x, gradient_y = np.gradient(pixels)
        edge_density = float(np.mean(np.hypot(gradient_x, gradient_y) > 18))
        return ImageFeatures(entropy, edge_density, float(np.var(pixels)))

class VideoFeatureExtractor(BaseFeatureExtractor):
    def extract(self, path: Path) -> VideoFeatures:
        """Safe placeholder until an FFmpeg metadata adapter is added."""
        return VideoFeatures()

