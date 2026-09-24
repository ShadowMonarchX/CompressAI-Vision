import math
import numpy as np
from PIL import Image

def evaluate(original, compressed) -> dict[str, float]:
    with Image.open(original) as a, Image.open(compressed) as b:
        x = np.asarray(a.convert("RGB").resize((256, 256)), dtype=np.float32)
        y = np.asarray(b.convert("RGB").resize((256, 256)), dtype=np.float32)
    mse = float(np.mean((x-y)**2)); psnr = 99.0 if mse == 0 else 20 * math.log10(255 / math.sqrt(mse))
    mux, muy = x.mean(), y.mean(); vx, vy = x.var(), y.var(); cov = np.mean((x-mux)*(y-muy))
    ssim = float((2*mux*muy+6.5025)*(2*cov+58.5225) / ((mux*mux+muy*muy+6.5025)*(vx+vy+58.5225)))
    return {"ssim": max(0., min(1., ssim)), "psnr": psnr}
