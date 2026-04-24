# REPORT_ITERATION_21.md
## Timestamp & Duration
- Completed: 2026-04-03 16:35:52
- Mega iteration: 19
- Pass 1 (LHS): 2.38s
- Pass 2 (DE): 189.87s
- Elapsed since start: 10746.24s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; narrative (decline during hunt, recovery after t=6.5), crash MSE ratio, hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** when certification score improves.
- R² hist ≥ 0.848, narrative mins: decline_rel ≥ 0.004, recovery_rel ≥ 0.006.

## The Scores (global best this mega)
- Composite loss: 0.248367
- R² historical with Eh: 0.0031
- R² historical with Eh=0: -2.2067
- Baseline oscillation (std G): 0.05870
- Full criteria met: False
- Certification score this mega: 0.364301
- Best certified score so far: none yet
- Crash-window MSE ratio: 39.4539
- narr decline_rel / recovery_rel: 0.87272 / 5.34177

## Visual Evidence
See `optimization_logs/final_g07_*.png` and `optimization_logs/checkpoints/`.
