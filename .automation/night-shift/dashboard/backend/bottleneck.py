"""NAE Live Dashboard — bottleneck panel judgment.

Deterministic and threshold-based, grounded only in values already read
this poll cycle. No trend analysis, no ML, no guessing: if a reading is
missing, the verdict is UNKNOWN rather than a fabricated guess (explicit
product requirement — don't display a guess as a fact).
"""
from __future__ import annotations

HIGH_THRESHOLD = 85.0


def compute_bottleneck(
    *,
    gpu_pct: float | None,
    cpu_pct: float | None,
    ram_pct: float | None,
    ollama_active: bool,
    threshold: float = HIGH_THRESHOLD,
) -> dict:
    readings = {"GPU": gpu_pct, "CPU": cpu_pct, "RAM": ram_pct}
    known = {k: v for k, v in readings.items() if v is not None}

    base = {"gpu_pct": gpu_pct, "cpu_pct": cpu_pct, "ram_pct": ram_pct, "threshold": threshold}

    if not known:
        return {**base, "resource": "UNKNOWN", "label": "UNKNOWN — no resource readings available"}

    top_resource, top_value = max(known.items(), key=lambda kv: kv[1])

    if top_value < threshold:
        return {**base, "resource": "NONE", "label": "NONE — all resources nominal"}

    label = top_resource
    if top_resource == "GPU" and ollama_active:
        label = "GPU / LLM DECODING"

    return {**base, "resource": top_resource, "label": label}
