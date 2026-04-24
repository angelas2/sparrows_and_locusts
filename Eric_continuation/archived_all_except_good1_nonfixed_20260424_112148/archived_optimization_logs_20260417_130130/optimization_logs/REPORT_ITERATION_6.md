# REPORT_ITERATION_6.md
## Timestamp & Duration
- Completed: 2026-04-17 00:00:44
- Mega iteration: 4
- Pass 1 (LHS): 14.71s
- Pass 2 (DE): 607.82s
- Elapsed since start: 2474.09s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; narrative (decline during hunt, recovery after t=6.5), crash MSE ratio, hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** when certification score improves.
- R² hist ≥ 0.848, narrative mins: decline_rel ≥ 0.004, recovery_rel ≥ 0.006.

## The Scores (global best this mega)
- Composite loss: 0.146771
- R² historical with Eh: 0.4751
- R² historical with Eh=0: -0.0035
- Baseline oscillation (std G): 0.07531
- Full criteria met: False
- Certification score this mega: 0.850515
- Best certified score so far: none yet
- Crash-window MSE ratio: 5.4416
- narr decline_rel / recovery_rel: 0.83612 / 4.15677

## Visual Evidence
See `optimization_logs/final_*.png` and `optimization_logs/checkpoints/`.

Per SPEC §5 (latest 12y snapshot): `plot_N.png` in this folder.

![plot_N](plot_N.png)
