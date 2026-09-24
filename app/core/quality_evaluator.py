import math
from pathlib import Path
import numpy as np
from PIL import Image

class QualityEvaluator:
    def __init__(self, ssim_threshold: float = .90): self.ssim_threshold = ssim_threshold
    def evaluate(self, original: Path, compressed: Path) -> dict[str, float]:
        with Image.open(original) as a, Image.open(compressed) as b:
            x = np.asarray(a.convert("RGB").resize((256, 256)), dtype=np.float32)
            y = np.asarray(b.convert("RGB").resize((256, 256)), dtype=np.float32)
        mse = float(np.mean((x-y)**2)); psnr = 99.0 if mse == 0 else 20 * math.log10(255 / math.sqrt(mse))
        mux, muy = x.mean(), y.mean(); vx, vy = x.var(), y.var(); cov = np.mean((x-mux)*(y-muy))
        ssim = (2*mux*muy+6.5025)*(2*cov+58.5225) / ((mux*mux+muy*muy+6.5025)*(vx+vy+58.5225))
        return {"ssim": max(0., min(1., float(ssim))), "psnr": psnr}

evaluate = QualityEvaluator().evaluate
