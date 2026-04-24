# REPORT_ITERATION_29.md
## Timestamp & Duration
- Completed: 2026-04-03 08:05:00
- Mega iteration: 27
- Pass 1 (LHS): 2.53s
- Pass 2 (DE): 210.11s
- Elapsed since start: 5940.23s

## The Code Changes
- Outer loop until success: R² hist ≥ 0.851, baseline G std ≥ 0.022, loss ≤ 0.45, hunting R² gain ≥ 0.035.
- `working_bounds` narrow around best each mega (full box reset every 12 megas).
- Pass 1: LHS seed varies per mega; SPEC 30s/10% → speed recovery.
- Pass 2: DE on `working_bounds`, seeds vary per mega.
- Good snapshots saved under `optimization_logs/checkpoints/good_*` when loss ≤ 1.25 or R² ≥ 0.72.

## The Scores (global best this mega)
- Composite loss: 0.119453
- R² historical with Eh: 0.4992
- R² historical with Eh=0: -0.7818
- Baseline oscillation (std G): 0.04411
- Success criteria met: False
- Crash-window MSE ratio (no-hunt / with-hunt): 9.5105 (need ≥ 1.08 for hunt to explain dip)

## Visual Evidence
See `optimization_logs/final_*.png` and `optimization_logs/checkpoints/`.
