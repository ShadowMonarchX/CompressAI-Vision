"""Pure media-feature extraction used by compression parameter predictors.

The extractors in this module deliberately know nothing about FastAPI, jobs, or
storage. They accept a filesystem path and return immutable value objects. That
makes the feature calculations easy to test and keeps orchestration in the
service layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class ImageFeatures:
    """Numerical characteristics used by the image quality heuristic.

    ``entropy`` measures how evenly brightness values are distributed;
    ``edge_density`` estimates how much high-frequency detail is present; and
    ``variance`` measures overall brightness contrast. These values are derived
    from a bounded grayscale sample rather than the full image, so prediction
    remains fast for very large uploads.
    """

    entropy: float
    edge_density: float
    variance: float


@dataclass(frozen=True)
class VideoFeatures:
    """Reserved metadata shape for a future FFmpeg-backed video extractor."""

    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0


class BaseFeatureExtractor(ABC):
    """Interface shared by image and future video feature extractors."""

    @abstractmethod
    def extract(self, path: Path) -> ImageFeatures | VideoFeatures:
        """Extract plain numerical features from ``path``."""


class ImageFeatureExtractor(BaseFeatureExtractor):
    """Extract bounded grayscale statistics from an image file."""

    max_sample_size = 512
    edge_threshold = 18.0

    def extract(self, path: Path) -> ImageFeatures:
        """Return entropy, edge density, and variance for ``path``.

        The image is converted to grayscale because the current predictor only
        needs luminance detail. Sampling preserves the source aspect ratio;
        stretching every image to a square would distort edge measurements.
        ``Image.open`` also validates that the path is a readable image and
        naturally propagates Pillow's useful file-format errors to callers.
        """
        with Image.open(path) as image:
            sample_size = self._sample_size(image.width, image.height)
            grayscale = image.convert("L").resize(sample_size, Image.Resampling.BILINEAR)
            pixels = np.asarray(grayscale, dtype=np.float32)

        # A 256-bin histogram maps each possible 8-bit brightness value to its
        # frequency. Zero-frequency bins are removed before log2 so entropy
        # never evaluates log2(0), which is undefined.
        histogram = np.histogram(pixels, bins=256, range=(0, 256))[0]
        probabilities = histogram[histogram > 0].astype(np.float64) / pixels.size
        entropy = float(-(probabilities * np.log2(probabilities)).sum())

        # np.gradient estimates brightness change horizontally and vertically.
        # The magnitude is an edge-strength estimate; the threshold converts it
        # into a density: the fraction of sampled pixels containing an edge.
        gradient_y, gradient_x = np.gradient(pixels)
        edge_strength = np.hypot(gradient_x, gradient_y)
        edge_density = float(np.mean(edge_strength > self.edge_threshold))

        return ImageFeatures(
            entropy=entropy,
            edge_density=edge_density,
            variance=float(np.var(pixels)),
        )

    def _sample_size(self, width: int, height: int) -> tuple[int, int]:
        """Calculate a bounded, aspect-ratio-preserving sample size."""
        if width < 1 or height < 1:
            raise ValueError("image dimensions must be positive")

        scale = min(1.0, self.max_sample_size / max(width, height))
        return max(1, round(width * scale)), max(1, round(height * scale))


class VideoFeatureExtractor(BaseFeatureExtractor):
    """Placeholder until FFmpeg metadata extraction is introduced."""

    def extract(self, path: Path) -> VideoFeatures:
        """Return the stable empty metadata shape for video inputs.

        Video transcoding currently obtains its parameters directly from the
        FFmpeg service path. Keeping this explicit placeholder avoids claiming
        that video metadata was analyzed when it was not.
        """
        return VideoFeatures()
