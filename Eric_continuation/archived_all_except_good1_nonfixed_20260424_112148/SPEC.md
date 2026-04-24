# SPEC.md: Autonomous Optimization of Lotka-Volterra Famine Model

## 1. The Objective
You are an autonomous AI optimization agent. Your goal is to iteratively run, analyze, and rewrite the `famine_model.py` script until it discovers a 16-parameter set for a 3-variable differential equation system (Sparrows, Locusts, Grain). 

A "successful" parameter set MUST achieve two physical realities:
1. **The Baseline:** Produce a natural, stable, oscillating limit cycle over a 30-year period (without flatlining into a stable equilibrium).
2. **The Crash:** Accurately fit the historical grain crash data when the hunting parameter (`Eh`) is applied between years 4.0 and 6.5.

## 2. The Need for Speed (The 30-Second Kill Switch)
Stiff ODE systems can cause the SciPy solver to hang indefinitely. **You must prioritize rapid, "close enough" iterations.**
- **Code the Timer:** You must modify the Python script to include a `time.time()` check inside the Pass 1 evaluation loop. 
- **The Fail-Fast Rule:** If the loop reaches the 10% completion mark and more than 30 seconds have elapsed, the script MUST immediately `break` the loop, print a "Speed Timeout" error, and exit.
- **The Fix:** When you detect a Speed Timeout in the logs, you must immediately rewrite the script to execute faster before trying again. You can do this by:
  - Drastically reducing sample sizes (e.g., lower `n_samples_pass1`).
  - Loosening the ODE solver tolerances (`atol`, `rtol`) in `solve_ivp`.
  - Aggressively narrowing bounds that force the math into stiff regimes.

## 3. Your Autonomous Freedom
You have almost absolute freedom to rewrite the python script to achieve the goal. You are starting with a Latin Hypercube Search (LHS) script that currently suffers from a "flatline trap" (the optimizer prefers safe flatlines over risky oscillations). 

To fix this, **you may modify, rewrite, or replace anything in the optimization logic.**
- Change the `log_bounds` search space.
- Add, remove, or alter any structural constraints, penalties, or thresholds inside `evaluate_params()`.
- Rewrite the scoring function (e.g., swapping R2 for Mean Squared Error or weighted penalties).
- Completely replace the LHS optimizer with a Genetic Algorithm, Differential Evolution, Particle Swarm, or any other strategy.

## 4. The Non-Negotiable Requirements (DO NOT VIOLATE)
1. **THE PHYSICS ARE LOCKED:** The mathematical equations inside `def system(t, y, Eh, *params):` are strictly off-limits. You cannot alter the core differential equations.
2. **The Two-Phase Simulation:** Every evaluation MUST consist of a 30-year unbothered baseline run (`Eh = 0.0`) and a 12-year historical run (`Eh` applied).
3. **No Hardcoded Cheats:** You must rely on an optimization algorithm to find the parameters. You cannot hardcode the final array.
4. **Trust the Data:** Do not invent arbitrary crash percentage requirements. The script must be judged on how well it fits the actual provided Chicago Rice Data.

## 5. Reporting & Observability (CRITICAL)
You must maintain a folder named `optimization_logs/` within the current directory. 

Whenever you make a significant logic change, or achieve a notable new "Best Score", generate a progress report named `REPORT_ITERATION_N.md` inside that folder. Each report must include:
1. **Timestamp & Duration:** The exact time the run completed and how many seconds it took.
2. **The Code Changes:** A summary of what optimization logic, bounds, or speed hacks you just applied and why.
3. **The Scores:** Your custom performance metric, R2, or loss score.
4. **Visual Evidence:** Modify `plot_results()` to use `plt.savefig('optimization_logs/plot_N.png')`. Include this image in the report.

## 6. Keep Going
1. You are not finished until the fit is almost perfect with hunting and there is not even a blip in the model with no hunting at the time the hunting model has a big dip