# REPORT_ITERATION_18.md
## Timestamp & Duration
- Completed: 2026-04-03 16:26:17
- Mega iteration: 16
- Pass 1 (LHS): 7.33s
- Pass 2 (DE): 5395.13s
- Elapsed since start: 10171.91s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; narrative (decline during hunt, recovery after t=6.5), crash MSE ratio, hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** when certification score improves.
- R² hist ≥ 0.848, narrative mins: decline_rel ≥ 0.004, recovery_rel ≥ 0.006.

## The Scores (global best this mega)
- Composite loss: 0.266705
- R² historical with Eh: -0.0730
- R² historical with Eh=0: -1.9921
- Baseline oscillation (std G): 0.02976
- Full criteria met: False
- Certification score this mega: 0.285657
- Best certified score so far: none yet
- Crash-window MSE ratio: 17.9292
- narr decline_rel / recovery_rel: 0.46987 / 0.18334

## Visual Evidence
See `optimization_logs/final_g07_*.png` and `optimization_logs/checkpoints/`.
