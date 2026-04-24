# REPORT_ITERATION_23.md
## Timestamp & Duration
- Completed: 2026-04-03 16:42:09
- Mega iteration: 21
- Pass 1 (LHS): 9.87s
- Pass 2 (DE): 179.91s
- Elapsed since start: 11123.85s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; narrative (decline during hunt, recovery after t=6.5), crash MSE ratio, hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** when certification score improves.
- R² hist ≥ 0.848, narrative mins: decline_rel ≥ 0.004, recovery_rel ≥ 0.006.

## The Scores (global best this mega)
- Composite loss: 0.238008
- R² historical with Eh: 0.0854
- R² historical with Eh=0: -2.1572
- Baseline oscillation (std G): 0.03797
- Full criteria met: False
- Certification score this mega: 0.448053
- Best certified score so far: none yet
- Crash-window MSE ratio: 111.9362
- narr decline_rel / recovery_rel: 0.67329 / 1.46273

## Visual Evidence
See `optimization_logs/final_g07_*.png` and `optimization_logs/checkpoints/`.
