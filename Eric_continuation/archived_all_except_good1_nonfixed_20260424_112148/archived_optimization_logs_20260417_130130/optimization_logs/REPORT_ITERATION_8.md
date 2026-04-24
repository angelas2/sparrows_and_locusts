# REPORT_ITERATION_8.md
## Timestamp & Duration
- Completed: 2026-04-17 00:25:35
- Mega iteration: 6
- Pass 1 (LHS): 11.92s
- Pass 2 (DE): 701.72s
- Elapsed since start: 3965.01s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; narrative (decline during hunt, recovery after t=6.5), crash MSE ratio, hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** when certification score improves.
- R² hist ≥ 0.848, narrative mins: decline_rel ≥ 0.004, recovery_rel ≥ 0.006.

## The Scores (global best this mega)
- Composite loss: 0.119000
- R² historical with Eh: 0.5156
- R² historical with Eh=0: 0.0930
- Baseline oscillation (std G): 0.03477
- Full criteria met: False
- Certification score this mega: 0.873141
- Best certified score so far: none yet
- Crash-window MSE ratio: 4.3852
- narr decline_rel / recovery_rel: 0.37970 / 0.11008

## Visual Evidence
See `optimization_logs/final_*.png` and `optimization_logs/checkpoints/`.

Per SPEC §5 (latest 12y snapshot): `plot_N.png` in this folder.

![plot_N](plot_N.png)
