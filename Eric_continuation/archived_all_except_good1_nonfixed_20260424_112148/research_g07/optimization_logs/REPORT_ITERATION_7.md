# REPORT_ITERATION_7.md
## Timestamp & Duration
- Completed: 2026-04-03 14:12:40
- Mega iteration: 5
- Pass 1 (LHS): 7.35s
- Pass 2 (DE): 187.60s
- Elapsed since start: 2154.58s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; narrative (decline during hunt, recovery after t=6.5), crash MSE ratio, hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** when certification score improves.
- R² hist ≥ 0.848, narrative mins: decline_rel ≥ 0.004, recovery_rel ≥ 0.006.

## The Scores (global best this mega)
- Composite loss: 0.331071
- R² historical with Eh: -0.4264
- R² historical with Eh=0: -2.1419
- Baseline oscillation (std G): 0.04960
- Full criteria met: False
- Certification score this mega: -0.076725
- Best certified score so far: none yet
- Crash-window MSE ratio: 21.0021
- narr decline_rel / recovery_rel: 0.99824 / 187.51424

## Visual Evidence
See `optimization_logs/final_g07_*.png` and `optimization_logs/checkpoints/`.
