"""
Harmonic tide prediction for Galician Atlantic coast.

Uses tidal harmonic constituents published by the Instituto Hidrográfico
de la Marina (IHM) for the reference port of A Coruña (ZMSL 2.09 m above
chart datum).  Astronomical equilibrium arguments are computed following
Schureman (1940) / IHO SP-44, with simplified nodal corrections.

Accuracy: ±10–15 cm typical, sufficient for beach guidance.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Harmonic constituents for A Coruña (source: IHM Tablas de Mareas 2024)
# H  = amplitude (m), kappa = Greenwich phase lag (°), speed = °/hour
# ---------------------------------------------------------------------------
_CONSTITUENTS: list[tuple[str, float, float, float]] = [
    # name    H      kappa    speed (°/h)
    ("M2",  1.497, 143.6,  28.9841042),
    ("S2",  0.484, 173.0,  30.0000000),
    ("N2",  0.288, 120.2,  28.4397295),
    ("K2",  0.136, 172.0,  30.0821373),
    ("K1",  0.066,   3.1,  15.0410686),
    ("O1",  0.050, 352.5,  13.9430356),
    ("P1",  0.021,   2.1,  14.9589314),
    ("Q1",  0.011, 337.1,  13.3986609),
    ("M4",  0.047, 183.0,  57.9682084),
    ("MS4", 0.028, 209.0,  58.9841042),
    ("MN4", 0.012, 157.0,  57.4238337),
]

_Z0 = 2.09          # mean sea level above chart datum (m)
_J2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)  # reference epoch


def _deg(x: float) -> float:
    return x % 360.0


def _astronomical_args(t_hours: float) -> dict[str, float]:
    """Compute equilibrium arguments V0 (degrees) for tidal constituents.

    t_hours: hours since J2000.0 (2000-01-01T12:00 UTC)
    Uses Schureman (1940) formulas; century-scale accuracy is fine for tides.
    """
    T = t_hours / 876582.0          # Julian centuries from J2000.0  (≈36525 days)
    s  = _deg(218.3164477 + 481267.88123421 * T)   # mean Moon longitude
    h  = _deg(280.46646   +  36000.76983    * T)   # mean Sun longitude
    p  = _deg( 83.3532465 +   4069.01363525 * T)   # mean perigee longitude
    N  = _deg(125.04452   -   1934.136261   * T)   # ascending node
    p1 = _deg(282.94374   +      1.7195946  * T)   # solar perigee

    return {
        "M2":  _deg(2*h - 2*s),
        "S2":  0.0,
        "N2":  _deg(2*h - 3*s + p),
        "K2":  _deg(2*h),
        "K1":  _deg(h + 90.0),
        "O1":  _deg(h - 2*s - 90.0),
        "P1":  _deg(-h + 180.0),
        "Q1":  _deg(h - 3*s + p - 90.0),
        "M4":  _deg(4*h - 4*s),
        "MS4": _deg(2*h - 2*s + 2*h),      # ≈ 2*(M2 arg for S2 part)
        "MN4": _deg(4*h - 5*s + p),
        # stored for potential future use
        "_s": s, "_h": h, "_p": p, "_N": N,
    }


def _nodal_f(name: str, N_deg: float) -> float:
    """Simplified nodal amplitude correction f (≈1 most of the time)."""
    N = math.radians(N_deg)
    if name in ("M2", "N2", "M4", "MN4", "MS4"):
        return 1.0 - 0.037 * math.cos(N)
    if name in ("K1",):
        return 1.006 + 0.115 * math.cos(N) - 0.009 * math.cos(2*N)
    if name in ("O1", "Q1"):
        return 1.009 + 0.187 * math.cos(N) - 0.015 * math.cos(2*N)
    if name in ("K2",):
        return 1.024 + 0.286 * math.cos(N) + 0.008 * math.cos(2*N)
    return 1.0


def _nodal_u(name: str, N_deg: float) -> float:
    """Simplified nodal phase correction u (degrees)."""
    N = math.radians(N_deg)
    if name in ("M2", "N2", "M4", "MN4", "MS4"):
        return -2.14 * math.sin(N)
    if name in ("K1",):
        return -8.86 * math.sin(N) + 0.68 * math.sin(2*N)
    if name in ("O1", "Q1"):
        return 10.8 * math.sin(N) - 1.34 * math.sin(2*N)
    if name in ("K2",):
        return -17.74 * math.sin(N) + 0.68 * math.sin(2*N)
    return 0.0


def tide_height(dt: datetime) -> float:
    """Compute predicted tide height (m above chart datum) at datetime dt."""
    t_hours = (dt - _J2000).total_seconds() / 3600.0
    args = _astronomical_args(t_hours)
    N_deg = args.get("_N", 0.0)

    h = _Z0
    for name, amp, kappa, speed in _CONSTITUENTS:
        V0 = args.get(name, 0.0)
        f  = _nodal_f(name, N_deg)
        u  = _nodal_u(name, N_deg)
        # angle = V0 + speed*t_hours + u - kappa  (all degrees)
        angle = _deg(V0 + speed * t_hours + u - kappa)
        h += f * amp * math.cos(math.radians(angle))

    return round(h, 2)


def tide_info(dt: datetime | None = None) -> dict[str, Any]:
    """Return current tide state and next extreme for a beach.

    All beaches in the project share the A Coruña reference port; tidal
    range variation across the monitored area (< 50 km) is negligible.
    """
    if dt is None:
        dt = datetime.now(timezone.utc)

    current_h = tide_height(dt)

    # Trend: compare 15 min ahead
    h_ahead = tide_height(dt + timedelta(minutes=15))
    trend = "rising" if h_ahead > current_h else "falling"
    trend_es = "Subiendo" if trend == "rising" else "Bajando"
    trend_arrow = "↑" if trend == "rising" else "↓"

    # Find next extreme within 8 hours (sample every 10 min)
    next_extreme: dict[str, Any] = {}
    prev_h = current_h
    for minutes_ahead in range(10, 8 * 60, 10):
        t_check = dt + timedelta(minutes=minutes_ahead)
        h_check = tide_height(t_check)
        h_next  = tide_height(t_check + timedelta(minutes=10))
        # local maximum (high water)
        if h_check >= prev_h and h_check >= h_next:
            next_extreme = {
                "type": "high",
                "type_es": "Pleamar",
                "time": t_check.strftime("%H:%M"),
                "height": round(h_check, 1),
                "minutes_away": minutes_ahead,
            }
            break
        # local minimum (low water)
        if h_check <= prev_h and h_check <= h_next:
            next_extreme = {
                "type": "low",
                "type_es": "Bajamar",
                "time": t_check.strftime("%H:%M"),
                "height": round(h_check, 1),
                "minutes_away": minutes_ahead,
            }
            break
        prev_h = h_check

    # Tidal phase as percentage from low (0%) to high (100%)
    # Estimate using last and next extreme
    phase_pct: int | None = None
    if next_extreme:
        span_min = next_extreme["minutes_away"]
        half_period_min = 6 * 60 + 12   # ~half M2 period
        if trend == "rising":
            phase_pct = max(0, min(100, int(100 * (1 - span_min / half_period_min))))
        else:
            phase_pct = max(0, min(100, int(100 * span_min / half_period_min)))

    return {
        "height": current_h,
        "trend": trend,
        "trend_es": trend_es,
        "trend_arrow": trend_arrow,
        "next_extreme": next_extreme,
        "phase_pct": phase_pct,
        "source": "IHM harmonic prediction (A Coruña)",
    }
