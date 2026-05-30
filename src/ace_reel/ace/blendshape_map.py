"""Map A2F-3D's (names, weights) blendshape stream onto the ARKit-52 pivot."""
from __future__ import annotations
from ace_reel.contracts.frame import _ARKIT_SET


def to_arkit_dict(names: list[str], weights: list[float]) -> dict[str, float]:
    if len(names) != len(weights):
        raise ValueError(f"names ({len(names)}) and weights ({len(weights)}) length mismatch")
    out: dict[str, float] = {}
    for name, w in zip(names, weights):
        if name in _ARKIT_SET:                 # drop A2F extras (extended tongue shapes etc.)
            out[name] = min(1.0, max(0.0, float(w)))
    return out
