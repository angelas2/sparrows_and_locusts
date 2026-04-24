# REPORT_ITERATION_5.md
## Timestamp & Duration
- Completed: 2026-04-16 23:50:21
- Mega iteration: 3
- Pass 1 (LHS): 17.30s
- Pass 2 (DE): 585.85s
- Elapsed since start: 1851.01s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; narrative (decline during hunt, recovery after t=6.5), crash MSE ratio, hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** when certification score improves.
- R² hist ≥ 0.848, narrative mins: decline_rel ≥ 0.004, recovery_rel ≥ 0.006.

## The Scores (global best this mega)
- Composite loss: 0.176917
- R² historical with Eh: 0.3225
- R² historical with Eh=0: -1.9721
- Baseline oscillation (std G): 0.02566
- Full criteria met: False
- Certification score this mega: 0.693763
- Best certified score so far: none yet
- Crash-window MSE ratio: 63.1450
- narr decline_rel / recovery_rel: 0.69969 / 1.57014

## Visual Evidence
See `optimization_logs/final_*.png` and `optimization_logs/checkpoints/`.

Per SPEC §5 (latest 12y snapshot): `plot_N.png` in this folder.

![plot_N](plot_N.png)
