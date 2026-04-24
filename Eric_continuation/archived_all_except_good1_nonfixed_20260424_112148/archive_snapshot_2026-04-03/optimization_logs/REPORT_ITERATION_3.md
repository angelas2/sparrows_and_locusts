# REPORT_ITERATION_3.md
## Timestamp & Duration
- Completed: 2026-04-03 09:06:42
- Mega iteration: 1
- Pass 1 (LHS): 14.46s
- Pass 2 (DE): 319.09s
- Elapsed since start: 333.89s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; stricter narrative (decline during hunt, recovery after t=6.5), higher crash MSE ratio, stronger hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** whenever certification score improves (pickier composite).
- R² hist ≥ 0.848, narrative mins: decline_rel ≥ 0.004, recovery_rel ≥ 0.006.

## The Scores (global best this mega)
- Composite loss: 0.127783
- R² historical with Eh: 0.4995
- R² historical with Eh=0: -0.8784
- Baseline oscillation (std G): 0.04361
- Full criteria met: False
- Certification score this mega: 0.877571
- Best certified score so far: none yet
- Crash-window MSE ratio: 240.5996
- narr decline_rel / recovery_rel: 0.84624 / 3.56637

## Visual Evidence
See `optimization_logs/final_*.png` and `optimization_logs/checkpoints/`.
