# REPORT_ITERATION_121.md
## Timestamp & Duration
- Completed: 2026-04-03 13:19:54
- Mega iteration: 119
- Pass 1 (LHS): 7.12s
- Pass 2 (DE): 204.15s
- Elapsed since start: 24833.74s

## The Code Changes
- Outer loop until success: R² hist ≥ 0.851, baseline G std ≥ 0.022, loss ≤ 0.45, hunting R² gain ≥ 0.035.
- `working_bounds` narrow around best each mega (full box reset every 12 megas).
- Pass 1: LHS seed varies per mega; SPEC 30s/10% → speed recovery.
- Pass 2: DE on `working_bounds`, seeds vary per mega.
- Good snapshots saved under `optimization_logs/checkpoints/good_*` when loss ≤ 1.25 or R² ≥ 0.72.

## The Scores (global best this mega)
- Composite loss: 0.103030
- R² historical with Eh: 0.5951
- R² historical with Eh=0: 0.2183
- Baseline oscillation (std G): 0.04365
- Success criteria met: False
- Crash-window MSE ratio (no-hunt / with-hunt): 7.0246 (need ≥ 1.08 for hunt to explain dip)

## Visual Evidence
See `optimization_logs/final_*.png` and `optimization_logs/checkpoints/`.
