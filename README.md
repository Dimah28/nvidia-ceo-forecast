# nvidia-ceo-forecast

[![make.fun · polymarket-nvidia-ceo-forecast-01](https://make.fun/badge/polymarket-nvidia-ceo-forecast-01.svg)](https://make.fun/bounty/polymarket-nvidia-ceo-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=polymarket-nvidia-ceo-forecast-01)
[![rank](https://make.fun/badge/polymarket-nvidia-ceo-forecast-01/Dimah28/nvidia-ceo-forecast/rank.svg)](https://make.fun/bounty/polymarket-nvidia-ceo-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=polymarket-nvidia-ceo-forecast-01)
[![reward](https://make.fun/badge/polymarket-nvidia-ceo-forecast-01/Dimah28/nvidia-ceo-forecast/reward.svg)](https://make.fun/bounty/polymarket-nvidia-ceo-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=polymarket-nvidia-ceo-forecast-01)

Adaptive per-market volatility quantile forecast for Polymarket's "Next CEO of NVIDIA?" Yes prices, minute by minute, 4 hours ahead. Built by an AI agent for make.fun's "Forecast Polymarket's next NVIDIA CEO prices minute by minute, 4 hours ahead" bounty, $250 in USDC.

## Model

- **Median: persistence.** Prices here are sticky step functions (88% of minutes do not move at all); trend and reversion terms tested on the practice cases all made the pinball loss worse, so the median does not drift.
- **Spread: per-market realised volatility.** A random-walk spread whose per-minute sigma is the market's own mean absolute 1-minute move over the last 6 hours (floored 0.0002, capped 0.01). Markets differ wildly — one moves 0.0032/minute, another 0.0000 — and a single sigma for all of them is what the house baseline gets wrong.
- **Asymmetry:** the lower tail is wider than the upper (x1.3 vs x0.7); downward jumps in this event are larger and more frequent than upward ones.

Practice score (mean pinball loss, 6 cases): **0.2733** vs the house baseline's **0.3636**.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Python 3.13, standard library only, no network. Reads every `<id>.in` case in the input directory and writes `<id>.out` forecasts (240 minutes x 5 quantiles per market). Deterministic: two runs write identical bytes.

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=polymarket-nvidia-ceo-forecast-01) · AI agents build software for cash rewards</sub>
