#!/usr/bin/env python3
"""
Re-fit from Wins (assigned)/good #1 after fixing sparrow death a3=1/3 and locust
death b4=1 (famine_model.FIXED_A3 / FIXED_B4).

Uses two-phase optimization: (1) relaxed penalties + full log bounds to find a
good MSE basin; (2) full default penalties, local DE + polish from phase-1 best.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import time

import numpy as np
from scipy.optimize import differential_evolution

_REPO = os.path.dirname(os.path.abspath(__file__))
GOOD1 = os.path.join(_REPO, "Wins (assigned)", "good #1", "checkpoint.json")
OPT_SUBDIR = "optimization_logs_good1_refit_fixed_death"

# Indices into 16-vector [lam,a2,b1,b3,b5,c1,c2,r_g,K_l,a3,b2,b4,S0,L0,G0,Eh]
IDX_14 = (0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 13, 14, 15)

_SOFT_ENV = {
    "FAMINE_OPT_LOG_ROOT": OPT_SUBDIR,
    "FAMINE_DE_ROUND_S": "1200",
    "FAMINE_EVAL_MAX_S": "55",
    # Effectively disable strict certification-style shaping for exploration
    "FAMINE_BASELINE_LAG5_CORR": "-2.0",
    "FAMINE_HUNT_S_REL_DROP": "-1.0",
    "FAMINE_LAG5_CORR_PEN_W": "0",
    "FAMINE_HUNT_S_PEN_W": "0",
    "FAMINE_BASELINE_PERIODICITY_W": "800.0",
    "FAMINE_BASELINE_CYCLE_SMOOTH_W": "12.0",
    "FAMINE_NARR_PEN_W": "35.0",
    "FAMINE_HUNTING_GAP_MIN": "-200.0",
}


def _apply_env(d: dict[str, str]) -> None:
    for k, v in d.items():
        os.environ[k] = v


def _reload_famine_model():
    import famine_model

    return importlib.reload(famine_model)


def load_seed_p14() -> np.ndarray:
    with open(GOOD1, encoding="utf-8") as f:
        ck = json.load(f)
    pl16 = ck["params_lin"]
    return np.array([float(pl16[i]) for i in IDX_14], dtype=float)


def _de(
    fm,
    bounds: list[tuple[float, float]],
    *,
    init_pop: np.ndarray | None,
    maxiter: int,
    popsize: int,
    seed: int,
    wall_s: float,
) -> object:
    t0 = time.time()

    def _cb(_xk, _c) -> bool:
        return (time.time() - t0) > wall_s

    kw: dict = dict(
        strategy="best1bin",
        maxiter=maxiter,
        popsize=popsize,
        mutation=(0.5, 1.25),
        recombination=0.65,
        disp=True,
        workers=1,
        polish=True,
        seed=seed % (2**31),
        callback=_cb,
    )
    if init_pop is not None:
        kw["init"] = init_pop
    else:
        kw["init"] = "sobol"

    return differential_evolution(fm.evaluate_params, bounds, **kw)


def main() -> int:
    if not os.path.isfile(GOOD1):
        print(f"Missing {GOOD1}", file=sys.stderr)
        return 1

    p14_seed = load_seed_p14()

    # ----- Phase 1: relaxed objective, full box -----
    _apply_env(_SOFT_ENV)
    fm = _reload_famine_model()
    fm.reset_solver_to_defaults()
    fm.best_score = float("inf")
    fm.best_params_log = None
    fm.working_bounds = [tuple(b) for b in fm.log_bounds]

    seed_log = fm.lin_to_log(p14_seed)
    dim = len(fm.working_bounds)
    pop1 = int(os.environ.get("FAMINE_REFIT_P1_POP", "7"))
    iter1 = int(os.environ.get("FAMINE_REFIT_P1_ITER", "70"))
    wall1 = float(os.environ.get("FAMINE_REFIT_P1_WALL", "5400"))
    num_pop = max(5, pop1 * dim)
    rng = np.random.default_rng(20250403)
    lows = np.array([b[0] for b in fm.working_bounds])
    highs = np.array([b[1] for b in fm.working_bounds])
    init1 = np.empty((num_pop, dim), dtype=float)
    init1[0] = np.clip(seed_log, lows, highs)
    for k in range(1, num_pop):
        init1[k] = lows + rng.random(dim) * (highs - lows)

    print("=== Phase 1: relaxed penalties, full bounds ===", flush=True)
    res1 = _de(fm, list(fm.working_bounds), init_pop=init1, maxiter=iter1, popsize=pop1, seed=11, wall_s=wall1)
    print(f"Phase1 fun={res1.fun:.6f} message={res1.message}", flush=True)

    # ----- Phase 2: strict defaults, local box around phase-1 -----
    for k in list(_SOFT_ENV.keys()):
        if k == "FAMINE_OPT_LOG_ROOT":
            continue
        os.environ.pop(k, None)
    os.environ["FAMINE_OPT_LOG_ROOT"] = OPT_SUBDIR

    fm = _reload_famine_model()
    fm.reset_solver_to_defaults()
    fm.best_score = float("inf")
    fm.best_params_log = None

    half = float(os.environ.get("FAMINE_REFIT_P2_LOG_HALF", "0.42"))
    center = np.asarray(res1.x, dtype=float)
    bounds2: list[tuple[float, float]] = []
    for i, (lo, hi) in enumerate(fm.log_bounds):
        c = float(center[i])
        lo_n = max(lo, c - half)
        hi_n = min(hi, c + half)
        if hi_n <= lo_n + 1e-9:
            lo_n, hi_n = lo, hi
        bounds2.append((lo_n, hi_n))

    fm.working_bounds = bounds2
    pop2 = int(os.environ.get("FAMINE_REFIT_P2_POP", "6"))
    iter2 = int(os.environ.get("FAMINE_REFIT_P2_ITER", "45"))
    wall2 = float(os.environ.get("FAMINE_REFIT_P2_WALL", "4200"))
    num_pop2 = max(5, pop2 * dim)
    lows2 = np.array([b[0] for b in bounds2])
    highs2 = np.array([b[1] for b in bounds2])
    init2 = np.empty((num_pop2, dim), dtype=float)
    init2[0] = np.clip(center, lows2, highs2)
    for k in range(1, num_pop2):
        init2[k] = lows2 + rng.random(dim) * (highs2 - lows2)

    print("=== Phase 2: full penalties, local refine ===", flush=True)
    res2 = _de(fm, bounds2, init_pop=init2, maxiter=iter2, popsize=pop2, seed=99, wall_s=wall2)
    print(f"Phase2 fun={res2.fun:.6f} message={res2.message}", flush=True)

    best_lin = fm.log_to_lin(res2.x)
    p_full = fm.expanded_params_lin(list(best_lin))
    loss = float(res2.fun)
    g_std, r2_e, r2_z = fm.metrics_for_report(p_full)

    out_dir = os.path.join(_REPO, fm.OPT_LOG_ROOT)
    os.makedirs(out_dir, exist_ok=True)
    out_json = os.path.join(out_dir, "good1_refit_checkpoint.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(
            {
                "source": GOOD1,
                "fixed_a3": fm.FIXED_A3,
                "fixed_b4": fm.FIXED_B4,
                "phase1_fun": float(res1.fun),
                "loss": loss,
                "de_message": res2.message,
                "nit": int(res2.nit),
                "params_log": [float(x) for x in res2.x],
                "params_lin_14": [float(x) for x in best_lin],
                "params_lin_16": [float(x) for x in p_full],
                "g_std": g_std,
                "r2_eh": r2_e,
                "r2_0": r2_z,
            },
            f,
            indent=2,
        )

    plot_prefix = os.path.join(out_dir, "good1_refit")
    fm.plot_results(list(p_full), plot_name=plot_prefix, save_plot_n=True, output_root=out_dir)

    print("\n=== good #1 refit (a3=1/3, b4=1) ===", flush=True)
    print(f"loss={loss:.6f}  g_std={g_std:.5f}  R2_eh={r2_e:.4f}  R2_0={r2_z:.4f}", flush=True)
    print(f"wrote {out_json}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
