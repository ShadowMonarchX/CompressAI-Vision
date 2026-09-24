"""Image quality scoring utilities."""
import math
from pathlib import Path
import numpy as np
from PIL import Image

class QualityEvaluator:
    def __init__(self, ssim_threshold: float = 0.90) -> None:
        if not 0 <= ssim_threshold <= 1:
            raise ValueError("ssim_threshold must be between 0 and 1")
        self.ssim_threshold = ssim_threshold

    def evaluate(self, original: Path, compressed: Path) -> dict[str, float]:
        with Image.open(original) as source, Image.open(compressed) as result:
            x = np.asarray(source.convert("RGB").resize((256, 256)), dtype=np.float32)
            y = np.asarray(result.convert("RGB").resize((256, 256)), dtype=np.float32)
        mse = float(np.mean((x - y) ** 2))
        psnr = 99.0 if mse == 0 else 20 * math.log10(255 / math.sqrt(mse))
        mux, muy = float(x.mean()), float(y.mean())
        vx, vy = float(x.var()), float(y.var())
        covariance = float(np.mean((x - mux) * (y - muy)))
        c1, c2 = 6.5025, 58.5225
        numerator = (2 * mux * muy + c1) * (2 * covariance + c2)
        denominator = (mux * mux + muy * muy + c1) * (vx + vy + c2)
        ssim = 1.0 if denominator == 0 else numerator / denominator
        return {"ssim": max(0.0, min(1.0, float(ssim))), "psnr": psnr}

evaluate = QualityEvaluator().evaluate

