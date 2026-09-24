from pathlib import Path
from PIL import Image
from .feature_extraction import image_features
from .parameter_predictor import HeuristicPredictor
from .quality_evaluator import evaluate

def compress(path: Path, output: Path, max_iterations: int, threshold: float) -> tuple[dict, dict]:
    params = HeuristicPredictor().predict_params(image_features(path)); quality = int(params["quality"])
    for _ in range(max_iterations):
        with Image.open(path) as im: im.convert("RGB").save(output, "JPEG", quality=quality, optimize=True)
        score = evaluate(path, output)
        if score["ssim"] >= threshold or quality >= 98: break
        quality = min(98, quality + 8)
    params["quality"] = quality
    return score, params
