"""Pure compression-parameter prediction strategies.

Predictors convert extracted feature values into immutable encoding settings.
They do not encode files or make service-layer decisions; ``AIService`` owns
the adjustment loop that applies these settings and evaluates the result.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import math

from .feature_extraction import ImageFeatures, VideoFeatures


@dataclass(frozen=True)
class CompressionParams:
    """Validated parameters returned by a compression predictor.

    ``quality`` is the Pillow/JPEG quality scale. ``crf`` is FFmpeg's constant
    rate-factor scale, where lower values generally preserve more quality.
    Both fields are present in one value object so image and video predictors
    can share the same interface, even though each encoder uses its own field.
    """

    codec: str
    quality: int = 80
    preset: str = "medium"
    crf: int = 28
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.codec.strip():
            raise ValueError("codec must not be empty")
        if not 1 <= self.quality <= 100:
            raise ValueError("quality must be between 1 and 100")
        if not 0 <= self.crf <= 51:
            raise ValueError("crf must be between 0 and 51")


class BaseParameterPredictor(ABC):
    """Interface for feature-to-parameter prediction strategies."""

    @abstractmethod
    def predict(self, features: ImageFeatures | VideoFeatures) -> CompressionParams:
        """Choose encoding parameters for extracted media features."""


class HeuristicPredictor(BaseParameterPredictor):
    """Choose conservative settings using lightweight image statistics."""

    # The output quality is intentionally bounded. Very low JPEG quality creates
    # obvious artifacts, while values above 92 produce large files for limited
    # visual benefit in this service's first-pass heuristic.
    min_image_quality = 55
    max_image_quality = 92

    def predict(self, features: ImageFeatures | VideoFeatures) -> CompressionParams:
        """Return parameters derived from an image or baseline video profile."""
        if isinstance(features, VideoFeatures):
            return CompressionParams(
                codec="libx264",
                crf=28,
                reason="video baseline",
            )
        if not isinstance(features, ImageFeatures):
            raise TypeError("HeuristicPredictor expects image or video features")

        self._validate_image_features(features)

        # Entropy is at most 8 bits for an 8-bit grayscale image. Edge density
        # is normalized to [0, 1]. Detail raises quality because textured images
        # reveal compression artifacts more readily than flat images.
        detail_score = features.edge_density * 100 + features.entropy * 3
        predicted_quality = round(58 + detail_score * 0.18)
        quality = max(self.min_image_quality, min(self.max_image_quality, predicted_quality))

        return CompressionParams(
            codec="JPEG",
            quality=quality,
            reason="entropy/edge-detail heuristic",
        )

    @staticmethod
    def _validate_image_features(features: ImageFeatures) -> None:
        """Reject NaN, infinity, and impossible normalized feature values."""
        values = (features.entropy, features.edge_density, features.variance)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("image features must be finite numbers")
        if features.entropy < 0 or features.edge_density < 0 or features.variance < 0:
            raise ValueError("image features must not be negative")
        if features.edge_density > 1:
            raise ValueError("edge_density must be between 0 and 1")
