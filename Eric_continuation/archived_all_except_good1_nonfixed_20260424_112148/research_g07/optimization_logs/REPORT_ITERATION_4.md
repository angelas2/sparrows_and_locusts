# REPORT_ITERATION_4.md
## Timestamp & Duration
- Completed: 2026-04-03 14:04:13
- Mega iteration: 2
- Pass 1 (LHS): 2.25s
- Pass 2 (DE): 1333.64s
- Elapsed since start: 1647.65s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; narrative (decline during hunt, recovery after t=6.5), crash MSE ratio, hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** when certification score improves.
- R² hist ≥ 0.848, narrative mins: decline_rel ≥ 0.004, recovery_rel ≥ 0.006.

## The Scores (global best this mega)
- Composite loss: 0.329925
- R² historical with Eh: -0.4208
- R² historical with Eh=0: -2.1431
- Baseline oscillation (std G): 0.04960
- Full criteria met: False
- Certification score this mega: -0.070956
- Best certified score so far: none yet
- Crash-window MSE ratio: 20.8719
- narr decline_rel / recovery_rel: 1.00074 / 225.73670

## Visual Evidence
See `optimization_logs/final_g07_*.png` and `optimization_logs/checkpoints/`.
