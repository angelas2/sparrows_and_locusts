# REPORT_ITERATION_64.md
## Timestamp & Duration
- Completed: 2026-04-03 10:07:53
- Mega iteration: 62
- Pass 1 (LHS): 2.38s
- Pass 2 (DE): 258.53s
- Elapsed since start: 13312.73s

## The Code Changes
- Outer loop until success: R² hist ≥ 0.851, baseline G std ≥ 0.022, loss ≤ 0.45, hunting R² gain ≥ 0.035.
- `working_bounds` narrow around best each mega (full box reset every 12 megas).
- Pass 1: LHS seed varies per mega; SPEC 30s/10% → speed recovery.
- Pass 2: DE on `working_bounds`, seeds vary per mega.
- Good snapshots saved under `optimization_logs/checkpoints/good_*` when loss ≤ 1.25 or R² ≥ 0.72.

## The Scores (global best this mega)
- Composite loss: 0.106863
- R² historical with Eh: 0.6052
- R² historical with Eh=0: 0.2338
- Baseline oscillation (std G): 0.05132
- Success criteria met: False
- Crash-window MSE ratio (no-hunt / with-hunt): 11.5643 (need ≥ 1.08 for hunt to explain dip)

## Visual Evidence
See `optimization_logs/final_*.png` and `optimization_logs/checkpoints/`.
