# REPORT_ITERATION_8.md
## Timestamp & Duration
- Completed: 2026-04-03 14:16:27
- Mega iteration: 6
- Pass 1 (LHS): 3.01s
- Pass 2 (DE): 223.65s
- Elapsed since start: 2381.55s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; narrative (decline during hunt, recovery after t=6.5), crash MSE ratio, hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** when certification score improves.
- R² hist ≥ 0.848, narrative mins: decline_rel ≥ 0.004, recovery_rel ≥ 0.006.

## The Scores (global best this mega)
- Composite loss: 0.268174
- R² historical with Eh: -0.0795
- R² historical with Eh=0: -1.9896
- Baseline oscillation (std G): 0.02950
- Full criteria met: False
- Certification score this mega: 0.278991
- Best certified score so far: none yet
- Crash-window MSE ratio: 16.5903
- narr decline_rel / recovery_rel: 0.47421 / 0.16191

## Visual Evidence
See `optimization_logs/final_g07_*.png` and `optimization_logs/checkpoints/`.
