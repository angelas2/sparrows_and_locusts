# REPORT_ITERATION_15.md
## Timestamp & Duration
- Completed: 2026-04-03 08:49:52
- Mega iteration: 13
- Pass 1 (LHS): 1.80s
- Pass 2 (DE): 92.95s
- Elapsed since start: 1222.76s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; stricter narrative (decline during hunt, recovery after t=6.5), higher crash MSE ratio, stronger hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** whenever certification score improves (pickier composite).
- R² hist ≥ 0.848, narrative mins: decline_rel ≥ 0.004, recovery_rel ≥ 0.006.

## The Scores (global best this mega)
- Composite loss: 0.078537
- R² historical with Eh: 0.7226
- R² historical with Eh=0: 0.1481
- Baseline oscillation (std G): 0.05763
- Full criteria met: False
- Certification score this mega: 1.107646
- Best certified score so far: none yet
- Crash-window MSE ratio: 73.7562
- narr decline_rel / recovery_rel: 0.76519 / 2.40469

## Visual Evidence
See `optimization_logs/final_*.png` and `optimization_logs/checkpoints/`.
