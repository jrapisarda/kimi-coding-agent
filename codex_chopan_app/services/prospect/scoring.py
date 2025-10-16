"""Prospect scoring helpers."""
from __future__ import annotations

from typing import Dict


def score(features: Dict[str, float]) -> float:
    weights = {"length": 0.3, "ai": 0.4, "arts": 0.3}
    return round(sum(features[key] * weights[key] for key in weights), 3)
