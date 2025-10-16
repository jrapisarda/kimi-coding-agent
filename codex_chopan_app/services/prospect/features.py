"""Feature extraction helpers."""
from __future__ import annotations

from typing import Dict


def extract_features(name: str) -> Dict[str, float]:
    length_score = min(len(name) / 30.0, 1.0)
    ai_signal = 1.0 if "ai" in name.lower() else 0.5
    arts_signal = 1.0 if "art" in name.lower() else 0.2
    return {"length": length_score, "ai": ai_signal, "arts": arts_signal}
