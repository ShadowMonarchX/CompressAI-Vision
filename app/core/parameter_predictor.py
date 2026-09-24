from typing import Protocol

class Predictor(Protocol):
    def predict_params(self, features: dict[str, float]) -> dict[str, int | str]: ...

class HeuristicPredictor:
    def predict_params(self, features: dict[str, float]) -> dict[str, int | str]:
        detail = features["edge_density"] * 100 + features["entropy"] * 3
        quality = max(55, min(92, round(58 + detail * .18)))
        return {"codec": "JPEG", "quality": quality, "reason": "entropy/edge-detail heuristic"}
