#!/usr/bin/env python3
"""Forecast Polymarket's "Next CEO of NVIDIA?" Yes prices, minute by minute, 4h ahead.

Model (per market, fitted only from the case's own 72h price history):
  - Median: persistence -- the price stays where it was at the checkpoint.
    Prices here are sticky step functions (88% of minutes do not move at all),
    and trend/reversion terms tested on the practice cases all made the
    pinball loss worse, so the median does not drift.
  - Spread: a random-walk spread whose per-minute sigma is the market's own
    recent realised volatility -- the mean absolute 1-minute move over the
    last 6 hours, floored at 0.0002 and capped at 0.01. Markets differ wildly
    (one moves 0.0032/minute, another 0.0000), and a single sigma for all of
    them is what the house baseline gets wrong: on the six practice cases
    this per-market sigma scores 0.2775 mean pinball loss against the
    baseline's 0.3636.
  - Asymmetry: the lower tail is wider than the upper (x1.3 vs x0.7). Downward
    jumps in this event are larger and more frequent than upward ones
    (the practice's big moves were collapses), worth a further ~0.004.
  - Quantiles: q_tau(h) = clamp(x + z_tau * sigma * sqrt(h) * side, 0, 1),
    rounded to 6 decimals, non-decreasing per row.

Stdlib only, no network, deterministic (same bytes on every run).
Reads $MAKEFUN_INPUT_DIR (else /input), writes $MAKEFUN_OUTPUT_DIR (else /output).
"""
import json
import math
import os

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

WINDOW_MIN = 360          # minutes of recent history used for realised volatility
SIGMA_FLOOR = 0.0002      # per-minute sigma floor (a dead market can still jump)
SIGMA_CAP = 0.01          # per-minute sigma cap
UP_FACTOR = 0.7           # spread multiplier above the median
DOWN_FACTOR = 1.3         # spread multiplier below the median

# Standard normal quantiles for the contest's levels, to 9 decimals.
Z = {0.05: -1.644853627, 0.25: -0.674489750, 0.5: 0.0,
     0.75: 0.674489750, 0.95: 1.644853627}


def _norm_ppf(p):
    """Inverse standard normal CDF (Acklam's rational approximation, ~1e-9).

    Only used when a case asks for a quantile level outside the table above;
    the contest always sends the five tabulated levels.
    """
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285984469534e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def z_for(tau):
    return Z.get(tau, _norm_ppf(tau))


def price6(x):
    """x clamped to [0, 1] and rounded to 6 decimals (0, never -0)."""
    return min(1.0, max(0.0, round(x, 6))) + 0.0


def forecast_market(prices, horizon, quantiles):
    """240 rows x 5 quantiles for one market."""
    x = prices[-1] if prices else 0.5
    w = prices[-WINDOW_MIN:] if len(prices) > WINDOW_MIN else list(prices)
    if len(w) > 1:
        mean_abs = sum(abs(w[i + 1] - w[i]) for i in range(len(w) - 1)) / (len(w) - 1)
    else:
        mean_abs = 0.0
    sigma = min(SIGMA_CAP, max(SIGMA_FLOOR, mean_abs))
    rows = []
    for h in range(1, horizon + 1):
        s = sigma * math.sqrt(h)
        row = []
        for tau in quantiles:
            z = z_for(tau)
            if z > 0:
                row.append(price6(x + z * s * UP_FACTOR))
            elif z < 0:
                row.append(price6(x + z * s * DOWN_FACTOR))
            else:
                row.append(price6(x))
        for j in range(1, len(row)):
            if row[j] < row[j - 1]:
                row[j] = row[j - 1]
        rows.append(row)
    return rows


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    names = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".in"))
    for name in names:
        case_id = name[: -len(".in")]
        with open(os.path.join(INPUT_DIR, name), "r", encoding="utf-8") as fh:
            case = json.load(fh)
        horizon = int(case.get("horizon_minutes", 240))
        quantiles = case.get("quantiles", [0.05, 0.25, 0.5, 0.75, 0.95])
        forecasts = []
        for m in case.get("markets", []):
            forecasts.append({
                "id": m["id"],
                "q": forecast_market(m.get("prices", []), horizon, quantiles),
            })
        out_path = os.path.join(OUTPUT_DIR, case_id + ".out")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"forecasts": forecasts}) + "\n")


if __name__ == "__main__":
    main()
