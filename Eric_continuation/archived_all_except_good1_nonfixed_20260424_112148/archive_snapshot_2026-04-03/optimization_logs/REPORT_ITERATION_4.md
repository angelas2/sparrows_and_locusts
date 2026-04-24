# REPORT_ITERATION_4.md
## Timestamp & Duration
- Completed: 2026-04-03 09:12:06
- Mega iteration: 2
- Pass 1 (LHS): 11.91s
- Pass 2 (DE): 311.76s
- Elapsed since start: 657.90s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; stricter narrative (decline during hunt, recovery after t=6.5), higher crash MSE ratio, stronger hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** whenever certification score improves (pickier composite).
- R² hist ≥ 0.848, narrative mins: decline_rel ≥ 0.004, recovery_rel ≥ 0.006.

## The Scores (global best this mega)
- Composite loss: 0.087234
- R² historical with Eh: 0.6817
- R² historical with Eh=0: -0.7914
- Baseline oscillation (std G): 0.06148
- Full criteria met: False
- Certification score this mega: 1.065500
- Best certified score so far: none yet
- Crash-window MSE ratio: 166.7067
- narr decline_rel / recovery_rel: 0.75482 / 2.33358

## Visual Evidence
See `optimization_logs/final_*.png` and `optimization_logs/checkpoints/`.
