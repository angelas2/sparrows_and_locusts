# REPORT_ITERATION_5.md
## Timestamp & Duration
- Completed: 2026-04-17 14:09:07
- Mega iteration: 3
- Pass 1 (LHS): 17.12s
- Pass 2 (DE): 2596.62s
- Elapsed since start: 4031.87s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; narrative (decline during hunt, recovery after t=6.5), crash MSE ratio, hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** when certification score improves.
- R² hist ≥ 0.862, narrative mins: decline_rel ≥ 0.006, recovery_rel ≥ 0.009.

## The Scores (global best this mega)
- Composite loss: 0.137342
- R² historical with Eh: 0.4426
- R² historical with Eh=0: -0.9577
- Baseline oscillation (std G): 0.06244
- Full criteria met: False
- Certification score this mega: 0.860515
- Best certified score so far: none yet
- Crash-window MSE ratio: 7.5780
- narr decline_rel / recovery_rel: 0.92074 / 11.84523

## Visual Evidence
See `optimization_logs_current/final_*.png` and `optimization_logs_current/checkpoints/`.

Per SPEC §5 (latest 12y snapshot): `plot_N.png` in this folder.

![plot_N](plot_N.png)
