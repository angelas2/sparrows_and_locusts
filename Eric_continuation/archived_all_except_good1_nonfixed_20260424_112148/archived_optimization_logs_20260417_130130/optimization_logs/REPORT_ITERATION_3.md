# REPORT_ITERATION_3.md
## Timestamp & Duration
- Completed: 2026-04-17 12:56:17
- Mega iteration: 1
- Pass 1 (LHS): 12.15s
- Pass 2 (DE): 730.87s
- Elapsed since start: 743.76s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; narrative (decline during hunt, recovery after t=6.5), crash MSE ratio, hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** when certification score improves.
- R² hist ≥ 0.862, narrative mins: decline_rel ≥ 0.006, recovery_rel ≥ 0.009.

## The Scores (global best this mega)
- Composite loss: 0.312260
- R² historical with Eh: -0.2373
- R² historical with Eh=0: -2.6353
- Baseline oscillation (std G): 0.05732
- Full criteria met: False
- Certification score this mega: 0.147394
- Best certified score so far: none yet
- Crash-window MSE ratio: 13.4961
- narr decline_rel / recovery_rel: 0.99792 / 394.01778

## Visual Evidence
See `optimization_logs/final_*.png` and `optimization_logs/checkpoints/`.

Per SPEC §5 (latest 12y snapshot): `plot_N.png` in this folder.

![plot_N](plot_N.png)
