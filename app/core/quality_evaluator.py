"""Image-quality metrics used by the compression adjustment loop.

The evaluator is intentionally framework-free: it compares two image paths and
returns plain numeric values. ``AIService`` decides what to do with those
values, such as increasing JPEG quality and trying another encoding pass.
"""

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


class QualityEvaluator:
    """Calculate approximate SSIM and PSNR for two images."""

    sample_size = 256

    def __init__(self, ssim_threshold: float = 0.90) -> None:
        if not math.isfinite(ssim_threshold) or not 0 <= ssim_threshold <= 1:
            raise ValueError("ssim_threshold must be a finite value between 0 and 1")
        self.ssim_threshold = ssim_threshold

    def evaluate(self, original: Path, compressed: Path) -> dict[str, float]:
        """Return bounded ``ssim`` and ``psnr`` scores.

        Both images are converted to RGB and sampled at the same dimensions.
        The sample preserves the original aspect ratio instead of stretching a
        portrait or landscape image into a square, which avoids introducing
        artificial edge and variance changes during evaluation.

        This is a global, lightweight SSIM approximation rather than a
        windowed implementation. It is sufficient for the service's retry
        heuristic, while avoiding the dependency and cost of a full image
        quality library.
        """
        target_size = self._target_size(original)
        source_pixels = self._read_rgb(original, target_size)
        result_pixels = self._read_rgb(compressed, target_size)

        mse = float(np.mean((source_pixels - result_pixels) ** 2))
        psnr = self._psnr(mse)
        ssim = self._ssim(source_pixels, result_pixels)
        return {"ssim": ssim, "psnr": psnr}

    def _target_size(self, path: Path) -> tuple[int, int]:
        """Read dimensions and return an aspect-ratio-preserving sample size."""
        with Image.open(path) as image:
            width, height = image.size
        if width < 1 or height < 1:
            raise ValueError("images must have positive dimensions")
        scale = min(1.0, self.sample_size / max(width, height))
        return max(1, round(width * scale)), max(1, round(height * scale))

    @staticmethod
    def _read_rgb(path: Path, size: tuple[int, int]) -> np.ndarray:
        """Load, orient, resize, and normalize an image into float pixels."""
        with Image.open(path) as image:
            prepared = ImageOps.exif_transpose(image).convert("RGB")
            resized = prepared.resize(size, Image.Resampling.LANCZOS)
            return np.asarray(resized, dtype=np.float32)

    @staticmethod
    def _psnr(mse: float) -> float:
        """Calculate peak signal-to-noise ratio for 8-bit RGB pixels."""
        if mse <= 0:
            return 99.0
        return max(0.0, 20 * math.log10(255 / math.sqrt(mse)))

    @staticmethod
    def _ssim(source: np.ndarray, result: np.ndarray) -> float:
        """Calculate a bounded global SSIM approximation.

        The constants are the standard stabilizers for an 8-bit signal range.
        Means, variances, and covariance are computed over all RGB samples so
        luminance, contrast, and structural correlation each contribute.
        """
        source_mean, result_mean = float(source.mean()), float(result.mean())
        source_variance, result_variance = float(source.var()), float(result.var())
        covariance = float(np.mean((source - source_mean) * (result - result_mean)))
        c1, c2 = 6.5025, 58.5225
        numerator = (2 * source_mean * result_mean + c1) * (2 * covariance + c2)
        denominator = (
            (source_mean**2 + result_mean**2 + c1)
            * (source_variance + result_variance + c2)
        )
        if denominator == 0:
            return 1.0 if np.array_equal(source, result) else 0.0
        return max(0.0, min(1.0, float(numerator / denominator)))


evaluate = QualityEvaluator().evaluate
