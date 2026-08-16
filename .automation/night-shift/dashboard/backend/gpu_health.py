"""NAE Live Dashboard — GPU health judgment.

Deliberately narrow. On this workstation (Apple Silicon, no sudo used
anywhere in this dashboard — see collector.py's `read_thermal_pressure_raw`
docstring) the only real distress signal available is macOS's own
thermal-warning flag (`pmset -g therm`). GPU *utilization* is never used
as a health signal by itself: sustained high utilization is the expected,
healthy state while Ollama is decoding, not a fault.

Temperature (°C), power draw/limit (W), GPU clock (MHz), and performance
state (P0/P1/...) require `powermetrics` (sudo) or a custom native
IOReport/SMC client (private Apple frameworks) to sample real numbers —
this dashboard deliberately does neither (would mean either elevating
privileges or standing up new, unproven monitoring infrastructure next
to a live production LLM process). Those fields are always reported as
unavailable here rather than guessed; see monitor_state.py's
`gpu_extended` and BUILD_REPORT.md for the investigation trail.

XID error codes are an NVIDIA-driver-specific concept with no Apple
Silicon equivalent at all — not "unavailable", genuinely not applicable.
"""
from __future__ import annotations

UNKNOWN = "UNKNOWN"  # could exist in principle, not obtainable here
NOT_APPLICABLE = "N/A"  # concept doesn't apply to this hardware


def compute_gpu_health(*, gpu_stats: dict | None, thermal_pressure: str) -> dict:
    """`thermal_pressure` is collector.parse_thermal_pressure()'s output:
    'nominal' | 'elevated' | 'unknown'."""
    if gpu_stats is None:
        return {
            "status": "UNKNOWN",
            "reason": "GPU telemetry unavailable this cycle (ioreg read failed or returned nothing)",
            "thermal_throttle": UNKNOWN,
            "power_throttle": UNKNOWN,
            "xid_errors": None,
        }

    if thermal_pressure == "elevated":
        return {
            "status": "WARNING",
            "reason": "macOS recorded an elevated thermal warning level (pmset -g therm)",
            "thermal_throttle": "YES",
            "power_throttle": UNKNOWN,
            "xid_errors": None,
        }

    thermal_throttle = "NO" if thermal_pressure == "nominal" else UNKNOWN
    return {
        "status": "HEALTHY",
        "reason": None,
        "thermal_throttle": thermal_throttle,
        "power_throttle": UNKNOWN,
        "xid_errors": None,
    }
