# REPORT_ITERATION_4.md
## Timestamp & Duration
- Completed: 2026-04-17 13:25:33
- Mega iteration: 2
- Pass 1 (LHS): 16.88s
- Pass 2 (DE): 654.75s
- Elapsed since start: 1417.59s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; narrative (decline during hunt, recovery after t=6.5), crash MSE ratio, hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** when certification score improves.
- R² hist ≥ 0.862, narrative mins: decline_rel ≥ 0.006, recovery_rel ≥ 0.009.

## The Scores (global best this mega)
- Composite loss: 0.137291
- R² historical with Eh: 0.4432
- R² historical with Eh=0: -0.9583
- Baseline oscillation (std G): 0.06306
- Full criteria met: False
- Certification score this mega: 0.861079
- Best certified score so far: none yet
- Crash-window MSE ratio: 7.6495
- narr decline_rel / recovery_rel: 0.92410 / 11.82253

## Visual Evidence
See `optimization_logs_current/final_*.png` and `optimization_logs_current/checkpoints/`.

Per SPEC §5 (latest 12y snapshot): `plot_N.png` in this folder.

![plot_N](plot_N.png)
