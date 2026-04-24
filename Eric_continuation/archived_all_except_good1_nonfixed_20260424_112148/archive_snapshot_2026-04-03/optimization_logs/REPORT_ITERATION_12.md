# REPORT_ITERATION_12.md
## Timestamp & Duration
- Completed: 2026-04-03 10:01:35
- Mega iteration: 10
- Pass 1 (LHS): 6.91s
- Pass 2 (DE): 379.65s
- Elapsed since start: 3626.76s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; stricter narrative (decline during hunt, recovery after t=6.5), higher crash MSE ratio, stronger hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** whenever certification score improves (pickier composite).
- R² hist ≥ 0.848, narrative mins: decline_rel ≥ 0.004, recovery_rel ≥ 0.006.

## The Scores (global best this mega)
- Composite loss: 0.081610
- R² historical with Eh: 0.7136
- R² historical with Eh=0: -0.5426
- Baseline oscillation (std G): 0.03918
- Full criteria met: False
- Certification score this mega: 1.098147
- Best certified score so far: none yet
- Crash-window MSE ratio: 129.6445
- narr decline_rel / recovery_rel: 0.70957 / 1.34878

## Visual Evidence
See `optimization_logs/final_*.png` and `optimization_logs/checkpoints/`.
