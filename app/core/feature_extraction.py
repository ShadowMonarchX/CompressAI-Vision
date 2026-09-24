from pathlib import Path
import numpy as np
from PIL import Image

def image_features(path: Path) -> dict[str, float]:
    with Image.open(path) as im:
        a = np.asarray(im.convert("L").resize((min(512, im.width), min(512, im.height))), dtype=np.float32)
    hist = np.histogram(a, bins=256, range=(0, 256), density=True)[0]
    entropy = float(-(hist[hist > 0] * np.log2(hist[hist > 0])).sum())
    gx, gy = np.gradient(a)
    return {"entropy": entropy, "edge_density": float(np.mean(np.hypot(gx, gy) > 18)),
            "variance": float(np.var(a))}
