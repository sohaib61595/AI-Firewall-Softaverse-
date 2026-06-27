"""
model.py
========
Loads the trained sklearn pipeline and exposes a `predict()` function
for use by the FastAPI app.
"""

import os
import re
from typing import List
from dataclasses import dataclass, field

import joblib
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

# ─── Category metadata ────────────────────────────────────────────────────────
CATEGORY_META = {
    "SAFE": {
        "verdict": "SAFE",
        "explanation": "This prompt appears legitimate. No malicious patterns detected.",
        "color": "#00ff88",
    },
    "JAILBREAK": {
        "verdict": "BLOCKED",
        "explanation": "Direct jailbreak attempt detected — trying to override the AI's safety guidelines.",
        "color": "#ff3366",
    },
    "ROLE_PLAY_BYPASS": {
        "verdict": "BLOCKED",
        "explanation": "Role-play bypass detected — using fictional framing to elicit restricted content.",
        "color": "#ff9500",
    },
    "PAYLOAD_INJECTION": {
        "verdict": "BLOCKED",
        "explanation": "Payload injection detected — embedded system-level override commands in the prompt.",
        "color": "#cc00ff",
    },
    "SOCIAL_ENGINEERING": {
        "verdict": "BLOCKED",
        "explanation": "Social engineering attempt — using false authority or context to bypass restrictions.",
        "color": "#ff6b35",
    },
    "DATA_EXFILTRATION": {
        "verdict": "BLOCKED",
        "explanation": "Data exfiltration attempt — trying to extract system prompt, context, or confidential instructions.",
        "color": "#4d9fff",
    },
}


@dataclass
class PredictionResult:
    verdict: str
    confidence: float
    category: str
    risk_score: int
    explanation: str
    top_features: List[dict] = field(default_factory=list)


class FirewallModel:
    def __init__(self):
        self._pipeline = None

    def load(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. "
                "Please run:  python backend/train_model.py"
            )
        self._pipeline = joblib.load(MODEL_PATH)
        print(f"[OK] Firewall model loaded from {MODEL_PATH}")

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    def predict(self, text: str) -> PredictionResult:
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load() first.")
        
        assert self._pipeline is not None, "Pipeline must be loaded"

        # Get class probabilities
        proba = self._pipeline.predict_proba([text])[0]
        classes = self._pipeline.classes_
        pred_idx = int(np.argmax(proba))
        category = classes[pred_idx]
        confidence = float(proba[pred_idx])

        meta = CATEGORY_META.get(category, CATEGORY_META["SAFE"])
        verdict = meta["verdict"]

        # Risk score: 0 for SAFE, else scale confidence to 50-100
        if verdict == "SAFE":
            risk_score = max(0, int((1 - confidence) * 50))
        else:
            risk_score = int(50 + confidence * 50)

        # Extract top contributing TF-IDF features
        top_features = self._get_top_features(text, category)

        return PredictionResult(
            verdict=verdict,
            confidence=round(confidence * 100, 1),
            category=category,
            risk_score=risk_score,
            explanation=meta["explanation"],
            top_features=top_features,
        )

    def _get_top_features(self, text: str, predicted_class: str) -> List[dict]:
        """Return the top N TF-IDF features contributing to the prediction.
        Works with both RandomForest (feature_importances_) and
        LogisticRegression (coef_).
        """
        try:
            assert self._pipeline is not None, "Pipeline must be loaded"
            tfidf = self._pipeline.named_steps["tfidf"]
            clf   = self._pipeline.named_steps["clf"]

            vec = tfidf.transform([text]).toarray()[0]
            feature_names = tfidf.get_feature_names_out()
            classes = list(clf.classes_)

            if predicted_class not in classes:
                return []

            class_idx = classes.index(predicted_class)

            # Support both RF (feature_importances_) and LR (coef_)
            if hasattr(clf, "feature_importances_"):
                importances = clf.feature_importances_
            elif hasattr(clf, "coef_"):
                # coef_ shape: (n_classes, n_features) for multiclass
                coef = clf.coef_
                if coef.ndim == 2:
                    importances = coef[class_idx]
                else:
                    importances = coef[0]
            else:
                return []

            # Weight TF-IDF values by feature importances / LR coefficients
            scores = vec * importances
            top_indices = np.argsort(np.abs(scores))[::-1][:8]

            result = []
            for idx in top_indices:
                if abs(scores[idx]) > 0:
                    result.append(
                        {"feature": feature_names[idx], "weight": round(float(abs(scores[idx])), 4)}
                    )
            return result
        except Exception:
            return []


# Singleton instance
firewall_model = FirewallModel()
