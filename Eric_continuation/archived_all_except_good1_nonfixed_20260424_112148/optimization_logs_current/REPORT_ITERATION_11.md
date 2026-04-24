# REPORT_ITERATION_11.md
## Timestamp & Duration
- Completed: 2026-04-17 15:39:15
- Mega iteration: 9
- Pass 1 (LHS): 9.10s
- Pass 2 (DE): 613.44s
- Elapsed since start: 9439.94s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; narrative (decline during hunt, recovery after t=6.5), crash MSE ratio, hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** when certification score improves.
- R² hist ≥ 0.862, narrative mins: decline_rel ≥ 0.006, recovery_rel ≥ 0.009.

## The Scores (global best this mega)
- Composite loss: 0.082912
- R² historical with Eh: 0.7153
- R² historical with Eh=0: 0.2747
- Baseline oscillation (std G): 0.08809
- Full criteria met: False
- Certification score this mega: 1.143558
- Best certified score so far: none yet
- Crash-window MSE ratio: 21.5777
- narr decline_rel / recovery_rel: 0.82431 / 3.68777

## Visual Evidence
See `optimization_logs_current/final_*.png` and `optimization_logs_current/checkpoints/`.

Per SPEC §5 (latest 12y snapshot): `plot_N.png` in this folder.

![plot_N](plot_N.png)
