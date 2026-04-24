import numpy as np
import sys
import os
import json
import shutil
import glob
import warnings
import time
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.optimize import differential_evolution
from scipy.stats import qmc

warnings.filterwarnings("ignore")

years = [1954, 1955, 1956, 1957, 1958, 1959, 1960, 1961, 1962, 1963, 1964, 1965]
unscaled_rice = [-39.69, -7.51, -44.61, 0.0, -32.53, -43.36, -59.23, -76.33, -85.63, -23.83, -30.49, -29.00]
rice_estimate_1958 = 59_400_000
rice_decrease_percent = 31.3
coefficients_kg = np.array(unscaled_rice) * 1_000_000
baseline_production = rice_estimate_1958 / (1 - (rice_decrease_percent / 100))
positive_rice_production = baseline_production + coefficients_kg

pre_shock_data = positive_rice_production[:5]
repeated_data_30 = np.array([pre_shock_data[i % 5] for i in range(30)])

numYears = 30
stepsPerYear = 30
t_span = (0, numYears)
t_eval = np.linspace(0, numYears, stepsPerYear * numYears)
t_span_12 = (0, 12)
t_eval_12 = np.linspace(0, 12, stepsPerYear * 12)

ATOL = 1e-3
RTOL = 1e-3
INTEG_WALL_S = 2.5
N_SAMPLES_PASS1 = 150
N_SAMPLES_PASS1_INITIAL = 150
DE_MAXITER = 45
DE_POPSIZE = 5
DE_MAXITER_INITIAL = 58
DE_POPSIZE_INITIAL = 5
PLOT_TAG = "final"
OPT_LOG_ROOT = os.environ.get(
    "FAMINE_OPT_LOG_ROOT",
    "optimization_logs_current",
)
CHECKPOINT_ROOT = os.path.join(OPT_LOG_ROOT, "checkpoints")
CHECKPOINT_SAVE_MAX_LOSS = 2500.0
FIXED_A3 = 1.0 / 3.0
FIXED_B4 = 1.0
DE_ROUNDS = 3

PASS1_SPEC_SECONDS = 30.0
PASS1_TOTAL_MAX_S = 240.0
DE_ROUND_MAX_S = 420.0
EVAL_TOTAL_MAX_S = 22.0
speed_tier = 0

SUCCESS_R2_HIST = float(os.environ.get("FAMINE_SUCCESS_R2", "0.862"))
SUCCESS_G_STD = float(os.environ.get("FAMINE_SUCCESS_G_STD", "0.028"))
SUCCESS_LOSS_MAX = float(os.environ.get("FAMINE_SUCCESS_LOSS_MAX", "0.48"))
SUCCESS_R2_MARGIN = float(os.environ.get("FAMINE_SUCCESS_R2_MARGIN", "0.045"))
CRASH_WINDOW_MSE_RATIO_MIN = float(os.environ.get("FAMINE_CRASH_RATIO_MIN", "1.28"))
NARRATIVE_DECLINE_REL_MIN = float(os.environ.get("FAMINE_NARR_DECL_MIN", "0.006"))
NARRATIVE_RECOVERY_REL_MIN = float(os.environ.get("FAMINE_NARR_REC_MIN", "0.009"))
NARRATIVE_PEN_W = float(os.environ.get("FAMINE_NARR_PEN_W", "165.0"))
HUNTING_GAP_MIN = float(os.environ.get("FAMINE_HUNTING_GAP_MIN", "0.016"))
# Baseline (Eh=0): encourage regular ~5y grain cycles; weights sum to 1.0
BASELINE_PERIODICITY_W = float(os.environ.get("FAMINE_BASELINE_PERIODICITY_W", "9000.0"))
BASELINE_CYCLE_SMOOTH_W = float(os.environ.get("FAMINE_BASELINE_CYCLE_SMOOTH_W", "45.0"))
MSE_BASE_WEIGHT = float(os.environ.get("FAMINE_MSE_BASE_WEIGHT", "0.30"))
MSE_HIST_WEIGHT = float(os.environ.get("FAMINE_MSE_HIST_WEIGHT", "0.70"))
HUNT_SPARROW_REL_DROP_MIN = float(os.environ.get("FAMINE_HUNT_S_REL_DROP", "0.012"))
BASELINE_LAG5_CORR_MIN = float(os.environ.get("FAMINE_BASELINE_LAG5_CORR", "0.88"))
HUNT_S_PEN_W = float(os.environ.get("FAMINE_HUNT_S_PEN_W", "350000"))
LAG5_CORR_PEN_W = float(os.environ.get("FAMINE_LAG5_CORR_PEN_W", "9000"))
MEGA_MAX = int(os.environ.get("FAMINE_MEGA_MAX", "10000"))
MEGA_TOTAL_WALL_S = float(os.environ.get("FAMINE_MEGA_WALL_S", str(45 * 24 * 3600)))
STOP_WHEN_CERTIFIED = int(os.environ.get("FAMINE_STOP_WHEN_CERTIFIED", "0"))
GOOD_R2_SAVE = float(os.environ.get("FAMINE_GOOD_R2", "0.76"))
GOOD_LOSS_SAVE = float(os.environ.get("FAMINE_GOOD_LOSS", "1.05"))

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
BEST_RESULTS_DIR = os.path.join(
    _REPO_ROOT, os.environ.get("FAMINE_BEST_RESULTS_DIR", "BEST_RESULTS")
)

os.makedirs(OPT_LOG_ROOT, exist_ok=True)
os.makedirs(CHECKPOINT_ROOT, exist_ok=True)


def rebuild_time_grids():
    global t_eval, t_eval_12
    t_eval = np.linspace(0, numYears, stepsPerYear * numYears)
    t_eval_12 = np.linspace(0, 12, stepsPerYear * 12)


def reset_solver_to_defaults():
    global ATOL, RTOL, INTEG_WALL_S, stepsPerYear, speed_tier
    ATOL = 1e-3
    RTOL = 1e-3
    INTEG_WALL_S = 2.5
    stepsPerYear = 30
    speed_tier = 0
    rebuild_time_grids()


def narrow_working_bounds(center_log, width_frac=0.38):
    global working_bounds
    new_b = []
    for i, c in enumerate(center_log):
        lo0, hi0 = log_bounds[i]
        span = (hi0 - lo0) * width_frac
        lo = max(lo0, float(c) - span)
        hi = min(hi0, float(c) + span)
        if hi <= lo:
            lo, hi = lo0, hi0
        new_b.append((lo, hi))
    working_bounds = new_b


def pivot_working_bounds(mega):
    global working_bounds
    rng = np.random.default_rng(int(10007 + mega * 17) % (2**32))
    new_b = []
    for i, (lo, hi) in enumerate(working_bounds):
        lo0, hi0 = log_bounds[i]
        mid = 0.5 * (lo + hi)
        span = (hi - lo) * rng.uniform(1.2, 1.55)
        jitter = (hi0 - lo0) * 0.04 * (rng.random() - 0.5)
        lo_n = max(lo0, mid - 0.5 * span + jitter)
        hi_n = min(hi0, mid + 0.5 * span + jitter)
        if hi_n <= lo_n + 1e-9:
            lo_n, hi_n = lo0, hi0
        new_b.append((lo_n, hi_n))
    working_bounds = new_b
    print(f"[pivot] mega={mega} expanded/jittered working_bounds", file=sys.stderr)


def apply_speed_recovery(reason):
    global ATOL, RTOL, INTEG_WALL_S, stepsPerYear, speed_tier
    speed_tier += 1
    print(f"[speed recovery tier {speed_tier}] {reason}", file=sys.stderr)
    ATOL = min(ATOL * 2.5, 2e-2)
    RTOL = min(RTOL * 2.5, 2e-2)
    INTEG_WALL_S = max(0.7, INTEG_WALL_S * 0.7)
    if stepsPerYear > 14:
        stepsPerYear = max(14, int(stepsPerYear * 0.65))
        rebuild_time_grids()
        print(f"  -> stepsPerYear={stepsPerYear}, atol={ATOL:.2e}, rtol={RTOL:.2e}, integ_wall={INTEG_WALL_S:.2f}s", file=sys.stderr)
    else:
        print(f"  -> atol={ATOL:.2e}, rtol={RTOL:.2e}, integ_wall={INTEG_WALL_S:.2f}s", file=sys.stderr)


def system(t, y, Eh, *params):
    S, L, G = y
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, b2 = params
    a3 = FIXED_A3
    b4 = FIXED_B4
    current_Eh = Eh if 4.0 <= t <= 6.5 else 0.0

    def f(Lv):
        return b1 + (b2 * Lv**2) / (b3**2 + Lv**2)

    dS = (lam * S * L) / (K_l + L) + (a2 * G * S) - (a3 * S) - (current_Eh * S)
    dL = f(L) * L - (b4 * L) - (b5 * S * L)
    dG = (r_g * (1 - G)) - (c1 * G * S) - (c2 * G * L) - (1.0 * G)
    return [dS, dL, dG]


def expanded_params_lin(p_opt):
    """14-vector (optimized, excluding fixed a3 and b4) -> full 16-vector for reporting/plots."""
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, b2, S0, L0, G0, Eh = p_opt
    return [
        lam,
        a2,
        b1,
        b3,
        b5,
        c1,
        c2,
        r_g,
        K_l,
        FIXED_A3,
        b2,
        FIXED_B4,
        S0,
        L0,
        G0,
        Eh,
    ]


log_bounds = [
    (-2, 2.5),
    (-4, -0.5),
    (-1, 1),
    (-3, -0.5),
    (-5, -0.5),
    (-4, -0.5),
    (-4, -0.5),
    (-0.5, 1.5),
    (-1, 3),
    (-2, 1),
    (-0.5, 1.5),
    (0.5, 2),
    (-1.3, -0.4),
    (-0.69897, 0.5),
]

working_bounds = [tuple(b) for b in log_bounds]

best_score = float("inf")
best_params_log = None
_checkpoint_seq = 0


def _checkpoint_dir():
    global _checkpoint_seq
    _checkpoint_seq += 1
    d = os.path.join(CHECKPOINT_ROOT, f"best_{_checkpoint_seq:04d}_{int(time.time())}")
    os.makedirs(d, exist_ok=True)
    return d


def save_checkpoint(p_log, p_lin, loss, mse_hist_eh, gap, penalty):
    ck_dir = _checkpoint_dir()
    p_lin_full = expanded_params_lin(list(p_lin))
    meta = {
        "loss": float(loss),
        "mse_hist_eh": float(mse_hist_eh),
        "hunting_gap": float(gap),
        "penalty": float(penalty),
        "speed_tier": speed_tier,
        "stepsPerYear": stepsPerYear,
        "atol": ATOL,
        "rtol": RTOL,
        "params_log": [float(x) for x in p_log],
        "params_lin": [float(x) for x in p_lin_full],
        "fixed_a3": FIXED_A3,
        "fixed_b4": FIXED_B4,
    }
    with open(os.path.join(ck_dir, "checkpoint.json"), "w") as f:
        json.dump(meta, f, indent=2)
    np.save(os.path.join(ck_dir, "params_log.npy"), np.array(p_log, dtype=float))
    plot_prefix = os.path.join(os.path.relpath(ck_dir, OPT_LOG_ROOT), "plot")
    try:
        plot_results(p_lin_full, plot_prefix, save_plot_n=False)
    except Exception as ex:
        print(f"  checkpoint plots failed: {ex}", file=sys.stderr)
    print(f"  checkpoint -> {ck_dir}/", file=sys.stderr)


def _make_timeout(start_eval):
    def timeout_event(t, y, Eh, *sys_args):
        if time.time() - start_eval > INTEG_WALL_S:
            return 0
        return 1

    timeout_event.terminal = True
    return timeout_event


def log_to_lin(p_log):
    return [10**x for x in p_log]


def lin_to_log(p_lin):
    return np.array([np.log10(max(float(x), 1e-300)) for x in p_lin])


def narrative_grain_shape(sol_hist):
    t_arr = sol_hist.t
    G_arr = sol_hist.y[2]
    g4 = float(np.interp(4.0, t_arr, G_arr))
    g65 = float(np.interp(6.5, t_arr, G_arr))
    mh = (t_arr >= 4.0) & (t_arr <= 6.5)
    g_hunt_min = float(np.min(G_arr[mh])) if np.any(mh) else g4
    mp = t_arr >= 7.25
    g_post = float(np.mean(G_arr[mp])) if np.any(mp) else g65
    decline_rel = (g4 - g_hunt_min) / (abs(g4) + 1e-9)
    recovery_rel = (g_post - g65) / (abs(g65) + 1e-9)
    decline_ok = decline_rel >= NARRATIVE_DECLINE_REL_MIN
    recovery_ok = recovery_rel >= NARRATIVE_RECOVERY_REL_MIN
    return {
        "g4": g4,
        "g65": g65,
        "g_hunt_min": g_hunt_min,
        "g_post_mean": g_post,
        "decline_rel": decline_rel,
        "recovery_rel": recovery_rel,
        "decline_ok": decline_ok,
        "recovery_ok": recovery_ok,
    }


def hunt_window_sparrow_suppression(p_lin_full):
    """True if mean sparrows S with Eh is below no-hunt S on 4–6.5y (hunting suppresses sparrows)."""
    if len(p_lin_full) == 14:
        p_lin_full = expanded_params_lin(p_lin_full)
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4, S0, L0, G0, Eh = p_lin_full
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, b2]
    sol_e = solve_ivp(
        system, t_span_12, [S0, L0, G0], t_eval=t_eval_12,
        args=(Eh, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL,
    )
    sol_z = solve_ivp(
        system, t_span_12, [S0, L0, G0], t_eval=t_eval_12,
        args=(0.0, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL,
    )
    if not sol_e.success or not sol_z.success:
        return False, 0.0, 0.0, 0.0, 0.0
    t_e = sol_e.t
    mask = (t_e >= 4.0) & (t_e <= 6.5)
    if not np.any(mask):
        return False, 0.0, 0.0, 0.0, 0.0
    S_h = sol_e.y[0][mask]
    S_z_i = np.interp(t_e[mask], sol_z.t, sol_z.y[0])
    mean_h = float(np.mean(S_h))
    mean_z = float(np.mean(S_z_i))
    denom = abs(mean_z) + 1e-9
    rel_drop = (mean_z - mean_h) / denom
    ok = mean_h < mean_z and rel_drop >= HUNT_SPARROW_REL_DROP_MIN
    return ok, rel_drop, mean_h, mean_z, float(mean_z - mean_h)


def baseline_five_year_cycle_quality(p_lin_full):
    """30y Eh=0 grain: strong lag-5 correlation => regular 5y cycles (pre-shock pattern)."""
    if len(p_lin_full) == 14:
        p_lin_full = expanded_params_lin(p_lin_full)
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4, S0, L0, G0, Eh = p_lin_full
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, b2]
    sol_b = solve_ivp(
        system, t_span, [S0, L0, G0], t_eval=t_eval,
        args=(0.0, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL,
    )
    if not sol_b.success:
        return False, float("nan"), float("nan")
    gb = sol_b.y[2][::stepsPerYear]
    if len(gb) < 6:
        return False, float("nan"), float("nan")
    c = np.corrcoef(gb[:-5], gb[5:])[0, 1]
    c = float(np.nan_to_num(c, nan=0.0))
    ok = c >= BASELINE_LAG5_CORR_MIN
    return ok, c, float(np.mean((gb[:-5] - gb[5:]) ** 2))


def crash_window_hunt_explains(p_lin):
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4, S0, L0, G0, Eh = p_lin
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, b2]
    scaling_factor = G0 / pre_shock_data[0]
    hist = positive_rice_production * scaling_factor
    sol_e = solve_ivp(
        system, t_span_12, [S0, L0, G0], t_eval=t_eval_12,
        args=(Eh, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL,
    )
    sol_z = solve_ivp(
        system, t_span_12, [S0, L0, G0], t_eval=t_eval_12,
        args=(0.0, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL,
    )
    ge = sol_e.y[2][::stepsPerYear]
    gz = sol_z.y[2][::stepsPerYear]
    cr = slice(6, 9)
    denom = float(np.mean(hist) ** 2) + 1e-12
    mse_cr_eh = float(np.mean((hist[cr] - ge[cr]) ** 2) / denom)
    mse_cr_0 = float(np.mean((hist[cr] - gz[cr]) ** 2) / denom)
    ratio = mse_cr_0 / (mse_cr_eh + 1e-12)
    explains = ratio >= CRASH_WINDOW_MSE_RATIO_MIN
    return explains, mse_cr_eh, mse_cr_0, ratio


def check_requirements(p_lin_opt):
    p_log = np.array([np.log10(max(float(x), 1e-300)) for x in p_lin_opt])
    loss = float(evaluate_params(p_log, track_best=False))
    p_lin_full = expanded_params_lin(p_lin_opt)
    g_std, r2_e, r2_z = metrics_for_report(p_lin_full)
    explains, mce, mc0, ratio = crash_window_hunt_explains(p_lin_full)
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4, S0, L0, G0, Eh = p_lin_full
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, b2]
    sol_e = solve_ivp(
        system, t_span_12, [S0, L0, G0], t_eval=t_eval_12,
        args=(Eh, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL,
    )
    narr = narrative_grain_shape(sol_e)
    hunt_s_ok, hunt_s_rel_drop, hunt_s_mean_eh, hunt_s_mean_z, hunt_s_abs_drop = hunt_window_sparrow_suppression(
        p_lin_full
    )
    base_cycle_ok, lag5_corr, lag5_mse = baseline_five_year_cycle_quality(p_lin_full)
    ok = (
        loss <= SUCCESS_LOSS_MAX
        and g_std >= SUCCESS_G_STD
        and r2_e >= SUCCESS_R2_HIST
        and (r2_e - r2_z) >= SUCCESS_R2_MARGIN
        and explains
        and narr["decline_ok"]
        and narr["recovery_ok"]
        and hunt_s_ok
        and base_cycle_ok
    )
    out = {
        "loss": loss,
        "g_std": g_std,
        "r2_eh": r2_e,
        "r2_0": r2_z,
        "hunting_r2_gain": r2_e - r2_z,
        "crash_mse_eh": mce,
        "crash_mse_0": mc0,
        "crash_mse_ratio_0_over_eh": ratio,
        "hunt_explains_crash_window": explains,
        "hunt_suppresses_sparrows": hunt_s_ok,
        "hunt_sparrow_rel_drop": hunt_s_rel_drop,
        "hunt_sparrow_mean_S_eh": hunt_s_mean_eh,
        "hunt_sparrow_mean_S_no_eh": hunt_s_mean_z,
        "baseline_lag5_corr": lag5_corr,
        "baseline_lag5_mse": lag5_mse,
        "baseline_five_year_cycle_ok": base_cycle_ok,
        **{f"narr_{k}": v for k, v in narr.items()},
    }
    return ok, out


def certification_score(info):
    return (
        float(info["r2_eh"])
        - 0.19 * min(float(info["loss"]), 3.0)
        + 2.45 * min(float(info.get("narr_recovery_rel", 0.0)), 0.12)
        + 1.25 * min(float(info.get("narr_decline_rel", 0.0)), 0.12)
    )


def write_certified_success(best_p_lin, info, mega, cert_score, ts=None):
    if ts is None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
    g_std = info["g_std"]
    r2_eh, r2_0 = info["r2_eh"], info["r2_0"]
    body = f"""# Famine model — certified best (live)

## Status
**Best certified so far** (run continues — this file updates when a better fit is found).

- Certified at: {ts}
- Mega iteration: {mega}
- Certification score: {cert_score:.6f} (higher = better fit + narrative)

## Narrative checks (hunting causes dip; recovery after hunt ends)
- Relative decline during hunt (4–6.5y): {info.get('narr_decline_rel', float('nan')):.5f} (min {NARRATIVE_DECLINE_REL_MIN})
- Relative recovery after t=6.5: {info.get('narr_recovery_rel', float('nan')):.5f} (min {NARRATIVE_RECOVERY_REL_MIN})
- Crash-window MSE ratio (no-hunt / with-hunt): {info.get('crash_mse_ratio_0_over_eh', float('nan')):.4f}

## Subjective physics (required for certification)
- **Hunting lowers sparrows** on 4–6.5y vs no-hunt: {info.get('hunt_suppresses_sparrows', False)} (rel drop {info.get('hunt_sparrow_rel_drop', float('nan')):.4f}, min {HUNT_SPARROW_REL_DROP_MIN})
- **Baseline 30y grain ~5y cycles** (lag-5 corr): {info.get('baseline_lag5_corr', float('nan')):.4f} (min {BASELINE_LAG5_CORR_MIN}), ok={info.get('baseline_five_year_cycle_ok', False)}

## The Algorithm
Uninterrupted mega-loop: LHS + DE; **no early exit** on first success. **SUCCESS_REPORT** updates when certification score improves. Penalties favor oscillating 30y baseline, historical fit with Eh, no spurious no-hunt crash fit, **decline during hunting**, **recovery after hunting stops**, and a stricter hunting-gap on MSE.

### Thresholds
- R² 12y with Eh ≥ {SUCCESS_R2_HIST}
- Baseline grain std ≥ {SUCCESS_G_STD}
- Composite loss ≤ {SUCCESS_LOSS_MAX}
- R² gain (Eh vs Eh=0) ≥ {SUCCESS_R2_MARGIN}
- Crash-window MSE ratio ≥ {CRASH_WINDOW_MSE_RATIO_MIN}

## The Best Array Found (certified)
```python
[{', '.join(f'{x:.8e}' for x in best_p_lin)}]
```

## Metrics
- Composite loss: {info['loss']:.6f}
- R² 12y with Eh: {r2_eh:.4f}
- R² 12y with Eh=0: {r2_0:.4f}
- Baseline grain std: {g_std:.5f}
"""
    with open("SUCCESS_REPORT.md", "w") as f:
        f.write(body)
    side = os.path.join(OPT_LOG_ROOT, "best_certified.json")
    payload = {
        "mega": mega,
        "cert_score": float(cert_score),
        "ts": ts,
        "params_lin": [float(x) for x in best_p_lin],
    }
    for k, v in info.items():
        if isinstance(v, (bool, np.bool_)):
            payload[k] = bool(v)
        elif isinstance(v, (float, np.floating, int, np.integer)):
            payload[k] = float(v)
        else:
            payload[k] = v
    with open(side, "w") as f:
        json.dump(payload, f, indent=2)

    try:
        export_top_level_best(best_p_lin, tag=f"mega_{mega}", meta=payload)
    except Exception as ex:
        print(f"top-level BEST_RESULTS export failed: {ex}", file=sys.stderr)


def export_top_level_best(best_p_lin, *, tag="", meta=None):
    """Write params + plots into top-level BEST_RESULTS/ (easy to find)."""
    os.makedirs(BEST_RESULTS_DIR, exist_ok=True)
    meta_out = dict(meta or {})
    meta_out.setdefault("params_lin", [float(x) for x in best_p_lin])
    meta_out.setdefault("export_tag", tag)
    meta_out.setdefault("export_dir", os.path.abspath(BEST_RESULTS_DIR))
    meta_out.setdefault("exported_at", time.strftime("%Y-%m-%d %H:%M:%S"))
    with open(os.path.join(BEST_RESULTS_DIR, "best_run.json"), "w") as f:
        json.dump(meta_out, f, indent=2)
    np.save(os.path.join(BEST_RESULTS_DIR, "params_lin.npy"), np.array(best_p_lin, dtype=float))
    plot_results(list(best_p_lin), plot_name="best", save_plot_n=True, output_root=BEST_RESULTS_DIR)
    sr = os.path.join(_REPO_ROOT, "SUCCESS_REPORT.md")
    if os.path.isfile(sr):
        shutil.copy2(sr, os.path.join(BEST_RESULTS_DIR, "SUCCESS_REPORT.md"))
    where = os.path.abspath(BEST_RESULTS_DIR)
    with open(os.path.join(BEST_RESULTS_DIR, "WHERE_AM_I.txt"), "w") as f:
        f.write("Best certified parameters and figures (updated whenever certification improves).\n\n")
        f.write(f"{where}\n")
    print(f"[export] Top-level best -> {where}/", file=sys.stderr)


def export_best_checkpoint_scan():
    """Pick lowest-loss checkpoint.json under known log trees and export to BEST_RESULTS."""
    roots = [
        os.path.join(_REPO_ROOT, "optimization_logs"),
        os.path.join(_REPO_ROOT, "optimization_logs_fit_a3_one_third_b4_one"),
    ]
    cands = []
    for r in roots:
        cands.extend(glob.glob(os.path.join(r, "checkpoints", "**", "checkpoint.json"), recursive=True))
    best = None
    for path in cands:
        try:
            with open(path, encoding="utf-8") as f:
                m = json.load(f)
            lo = float(m["loss"])
            if best is None or lo < best[0]:
                best = (lo, path, m)
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            continue
    if best is None:
        print("No checkpoints found to export.", file=sys.stderr)
        return
    pl = best[2]["params_lin"]
    if len(pl) == 14:
        pl = expanded_params_lin(pl)
    export_top_level_best(
        pl,
        tag=f"checkpoint_loss_{best[0]:.6f}",
        meta={
            "loss": best[0],
            "source_checkpoint": best[1],
            "mse_hist_eh": best[2].get("mse_hist_eh"),
            "note": "Exported from lowest-loss checkpoint scan (not necessarily certified).",
        },
    )


def save_good_snapshot(p_lin_opt, mega, info):
    loss = info["loss"]
    r2_e = info["r2_eh"]
    if loss > GOOD_LOSS_SAVE and r2_e < GOOD_R2_SAVE:
        return
    p_lin_full = expanded_params_lin(p_lin_opt)
    tag = f"good_mega{mega:04d}_r2_{r2_e:.4f}_loss_{loss:.4f}_{int(time.time())}"
    d = os.path.join(CHECKPOINT_ROOT, tag)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "good_snapshot.json"), "w") as f:
        json.dump(
            {**info, "mega": mega, "params_lin": [float(x) for x in p_lin_full], "fixed_a3": FIXED_A3, "fixed_b4": FIXED_B4},
            f,
            indent=2,
        )
    np.save(os.path.join(d, "params_lin.npy"), np.array(p_lin_full, dtype=float))
    plot_prefix = os.path.join(os.path.relpath(d, OPT_LOG_ROOT), "plot")
    plot_results(p_lin_full, plot_prefix)
    print(f"[good snapshot] -> {d}/", file=sys.stderr)


def evaluate_params(p_log, track_best=True):
    global best_score, best_params_log
    p = log_to_lin(p_log)
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, b2, S0, L0, G0, Eh = p
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, b2]

    eval_t0 = time.time()

    def _eval_budget():
        cap = EVAL_TOTAL_MAX_S + min(14.0, speed_tier * 3.5)
        if time.time() - eval_t0 > cap:
            return True
        return False

    start_eval = time.time()
    te = _make_timeout(start_eval)

    try:
        sol_base = solve_ivp(
            system, t_span, [S0, L0, G0], t_eval=t_eval,
            args=(0.0, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL, events=te,
        )
        if _eval_budget():
            return 1e6
        if not sol_base.success or sol_base.status == 1:
            return 1e6

        S_osc, L_osc, G_osc = sol_base.y
        sim_grains_base = G_osc[::stepsPerYear]

        penalty = 0.0
        if np.min(S_osc) < 0.001:
            penalty += (0.001 - np.min(S_osc)) * 1e5
        if np.min(L_osc) < 0.001:
            penalty += (0.001 - np.min(L_osc)) * 1e5
        if np.mean(L_osc) <= np.mean(S_osc):
            penalty += (np.mean(S_osc) - np.mean(L_osc)) * 1e5

        if len(sim_grains_base) > 1 and sim_grains_base[1] <= 0.05:
            penalty += (0.05 - sim_grains_base[1]) * 1e5

        if np.min(sim_grains_base) < (G0 * 0.75):
            penalty += (G0 * 0.75 - np.min(sim_grains_base)) * 5e5

        scaling_factor = G0 / pre_shock_data[0]
        target_scaled = repeated_data_30 * scaling_factor

        sim_range = float(np.max(sim_grains_base) - np.min(sim_grains_base))
        target_range = float(np.max(target_scaled) - np.min(target_scaled))
        if target_range > 1e-12 and sim_range < (target_range * 0.35):
            penalty += (target_range * 0.35 - sim_range) * 2e5

        g_std = float(np.std(G_osc))
        if g_std < 0.02:
            penalty += (0.02 - g_std) * 5e5

        if len(sim_grains_base) >= 6:
            d5 = sim_grains_base[:-5] - sim_grains_base[5:]
            period_mse = float(np.mean(d5 * d5))
            v_b = float(np.var(sim_grains_base))
            scale_p = period_mse / (v_b + 1e-10)
            penalty += BASELINE_PERIODICITY_W * min(scale_p, 25.0)

        if len(sim_grains_base) >= 3:
            d2y = np.diff(sim_grains_base, 2)
            vy = float(np.var(sim_grains_base)) + 1e-10
            rough_y = float(np.mean(d2y * d2y)) / vy
            penalty += BASELINE_CYCLE_SMOOTH_W * min(rough_y, 80.0)

        start_eval = time.time()
        te2 = _make_timeout(start_eval)
        sol_hist = solve_ivp(
            system, t_span_12, [S0, L0, G0], t_eval=t_eval_12,
            args=(Eh, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL, events=te2,
        )
        if _eval_budget():
            return 1e6
        if not sol_hist.success or sol_hist.status == 1:
            return 1e6

        narr = narrative_grain_shape(sol_hist)
        nd = max(0.0, NARRATIVE_DECLINE_REL_MIN - narr["decline_rel"])
        nr = max(0.0, NARRATIVE_RECOVERY_REL_MIN - narr["recovery_rel"])
        penalty += NARRATIVE_PEN_W * (nd * nd + nr * nr)

        sim_grains_hist = sol_hist.y[2][::stepsPerYear]

        start_eval = time.time()
        te3 = _make_timeout(start_eval)
        sol_hist0 = solve_ivp(
            system, t_span_12, [S0, L0, G0], t_eval=t_eval_12,
            args=(0.0, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL, events=te3,
        )
        if _eval_budget():
            return 1e6
        if not sol_hist0.success or sol_hist0.status == 1:
            return 1e6
        sim_grains_hist0 = sol_hist0.y[2][::stepsPerYear]

        t_h = sol_hist.t
        mask_h = (t_h >= 4.0) & (t_h <= 6.5)
        if np.any(mask_h):
            S_eh_w = sol_hist.y[0][mask_h]
            S_0_w = np.interp(t_h[mask_h], sol_hist0.t, sol_hist0.y[0])
            mean_z = float(np.mean(S_0_w)) + 1e-12
            rel_s = (float(np.mean(S_0_w)) - float(np.mean(S_eh_w))) / abs(mean_z)
            if rel_s < HUNT_SPARROW_REL_DROP_MIN:
                penalty += (HUNT_SPARROW_REL_DROP_MIN - rel_s) * HUNT_S_PEN_W

        if len(sim_grains_base) >= 6:
            c5 = float(np.nan_to_num(np.corrcoef(sim_grains_base[:-5], sim_grains_base[5:])[0, 1], nan=0.0))
            if c5 < BASELINE_LAG5_CORR_MIN:
                penalty += (BASELINE_LAG5_CORR_MIN - c5) * LAG5_CORR_PEN_W

        if len(sim_grains_hist) >= 9:
            min_crash = float(np.min(sim_grains_hist[6:9]))
            if min_crash > (np.min(sim_grains_base) * 0.55):
                penalty += (min_crash - np.min(sim_grains_base) * 0.55) * 3e5
        else:
            penalty += 1e6

        historical_scaled = positive_rice_production * scaling_factor
        denom_b = np.mean(target_scaled)
        denom_h = np.mean(historical_scaled)
        mse_base = np.mean(((target_scaled - sim_grains_base) / denom_b) ** 2)
        mse_hist_eh = np.mean(((historical_scaled - sim_grains_hist) / denom_h) ** 2)
        mse_hist_0 = np.mean(((historical_scaled - sim_grains_hist0) / denom_h) ** 2)

        gap = mse_hist_0 - mse_hist_eh
        if gap < HUNTING_GAP_MIN:
            penalty += (HUNTING_GAP_MIN - gap) * 1.45e4

        combined = MSE_BASE_WEIGHT * mse_base + MSE_HIST_WEIGHT * mse_hist_eh
        loss = combined + penalty

        if np.isnan(loss) or not np.isfinite(loss):
            return 1e6

        if track_best and loss < best_score:
            best_score = loss
            best_params_log = np.array(p_log, dtype=float).copy()
            print(f"New Best: {loss:.6f} (mse_hist_eh={mse_hist_eh:.5f} gap={gap:.5f} pen={penalty:.3f})")
            if loss <= CHECKPOINT_SAVE_MAX_LOSS:
                try:
                    save_checkpoint(list(p_log), p, loss, mse_hist_eh, gap, penalty)
                except Exception as ex:
                    print(f"  checkpoint failed: {ex}", file=sys.stderr)

        return loss
    except Exception:
        return 1e6


def pass1_lhs(lhs_seed=42):
    dim = len(working_bounds)
    lows = np.array([b[0] for b in working_bounds])
    highs = np.array([b[1] for b in working_bounds])
    sampler = qmc.LatinHypercube(dim, seed=int(lhs_seed) % (2**31))
    unit = sampler.random(n=N_SAMPLES_PASS1)
    scaled = qmc.scale(unit, lows, highs)

    pass1_t0 = time.time()
    ten_pct = max(1, int(0.1 * N_SAMPLES_PASS1))
    spec_done = False

    for i in range(N_SAMPLES_PASS1):
        if time.time() - pass1_t0 > PASS1_TOTAL_MAX_S:
            apply_speed_recovery(f"Pass 1 total wall {PASS1_TOTAL_MAX_S}s — ending LHS early after sample {i}")
            break
        evaluate_params(scaled[i])
        if not spec_done and i + 1 >= ten_pct and time.time() - pass1_t0 > PASS1_SPEC_SECONDS:
            apply_speed_recovery(
                "Speed Timeout (SPEC §2): Pass 1 exceeded 30s after 10% completion — tightening tolerances and ending LHS early"
            )
            spec_done = True
            break

    return time.time() - pass1_t0


def pass2_de(seed_base=42):
    global DE_MAXITER, DE_POPSIZE
    best_res = None
    total_elapsed = 0.0
    mi = DE_MAXITER_INITIAL
    ps = DE_POPSIZE_INITIAL
    for round_idx in range(DE_ROUNDS):
        de_t0 = time.time()

        def callback(xk, convergence):
            if time.time() - de_t0 > DE_ROUND_MAX_S:
                print(
                    f"DE round {round_idx + 1}/{DE_ROUNDS}: wall timeout ({DE_ROUND_MAX_S}s) — stopping this round",
                    file=sys.stderr,
                )
                return True
            return False

        round_maxiter = max(8, int(mi // max(1, DE_ROUNDS - round_idx)) + 8)
        res = differential_evolution(
            evaluate_params,
            working_bounds,
            strategy="best1bin",
            maxiter=round_maxiter,
            popsize=max(3, ps),
            mutation=(0.45, 1.35),
            recombination=0.65,
            disp=True,
            workers=1,
            polish=False,
            init="sobol",
            seed=int(seed_base + round_idx) % (2**31),
            callback=callback,
        )
        round_elapsed = time.time() - de_t0
        total_elapsed += round_elapsed
        if best_res is None or res.fun < best_res.fun:
            best_res = res
        if round_elapsed >= DE_ROUND_MAX_S - 0.5:
            apply_speed_recovery(f"DE round {round_idx + 1} used full wall — next round runs lighter")
        mi = max(10, int(mi * 0.88))
        ps = max(3, int(ps * 0.92))
    DE_MAXITER = mi
    DE_POPSIZE = ps
    if best_res is None:
        raise RuntimeError("differential_evolution returned no result")
    return best_res, total_elapsed


def plot_results(best_params, plot_name="plot", save_plot_n=True, output_root=None):
    root = OPT_LOG_ROOT if output_root is None else output_root
    os.makedirs(root, exist_ok=True)
    if len(best_params) == 14:
        best_params = expanded_params_lin(best_params)
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4, S0, L0, G0, Eh = best_params
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, b2]

    sol_30 = solve_ivp(
        system, t_span, [S0, L0, G0], t_eval=t_eval,
        args=(0.0, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL,
    )
    scaling_factor = G0 / pre_shock_data[0]
    target_scaled = repeated_data_30 * scaling_factor

    plt.figure(figsize=(10, 5))
    plt.plot(sol_30.t, sol_30.y[2], label="Simulated Grain (Natural Oscillation)", linewidth=2)
    plt.plot(np.arange(30), target_scaled, "o--", label="Synthetic 30-Year Target", color="red", alpha=0.6)
    plt.title("30-Year Natural Oscillation Fit (Pre-Shock Baseline)")
    plt.xlabel("Time (years)")
    plt.ylabel("Population Index")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(root, f"{plot_name}_30yr.png"))
    plt.close()

    sol_12 = solve_ivp(
        system, t_span_12, [S0, L0, G0], t_eval=t_eval_12,
        args=(Eh, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL,
    )
    sol_12_0 = solve_ivp(
        system, t_span_12, [S0, L0, G0], t_eval=t_eval_12,
        args=(0.0, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL,
    )
    historical_scaled = positive_rice_production * scaling_factor

    plt.figure(figsize=(10, 5))
    plt.plot(sol_12.t, sol_12.y[2], label="Simulated Grain (with Eh)", linewidth=2)
    plt.plot(np.arange(12), historical_scaled, "o-", label="Chicago Rice Data", color="red")
    plt.axvspan(4.0, 6.5, color="gray", alpha=0.2, label="Hunting Phase")
    plt.title(f"12-Year Historical Fit (Eh = {Eh:.4f})")
    plt.xlabel("Time (years)")
    plt.ylabel("Population Index")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(root, f"{plot_name}_12yr.png"))
    if save_plot_n:
        plt.savefig(os.path.join(root, "plot_N.png"))
    plt.close()

    # Sparrows only: same axes, no hunting vs hunting (no grain, no locusts on this figure)
    plt.figure(figsize=(10, 5))
    plt.plot(sol_12_0.t, sol_12_0.y[0], label="No hunting (Eh = 0)", linewidth=2, color="tab:green")
    plt.plot(sol_12.t, sol_12.y[0], label="With hunting", linewidth=2, color="tab:blue", alpha=0.9)
    plt.axvspan(4.0, 6.5, color="gray", alpha=0.2, zorder=0)
    plt.title("Sparrows only — same axes: with vs without hunting (12 years)")
    plt.xlabel("Time (years)")
    plt.ylabel("Sparrow population S")
    plt.legend(loc="best", framealpha=0.95)
    plt.grid(True)
    plt.savefig(os.path.join(root, f"{plot_name}_S_populations_12yr.png"))
    plt.close()

    # Locusts only: same axes, no hunting vs hunting (no grain, no sparrows on this figure)
    plt.figure(figsize=(10, 5))
    plt.plot(sol_12_0.t, sol_12_0.y[1], label="No hunting (Eh = 0)", linewidth=2, color="tab:green")
    plt.plot(sol_12.t, sol_12.y[1], label="With hunting", linewidth=2, color="tab:orange", alpha=0.9)
    plt.axvspan(4.0, 6.5, color="gray", alpha=0.2, zorder=0)
    plt.title("Locusts only — same axes: with vs without hunting (12 years)")
    plt.xlabel("Time (years)")
    plt.ylabel("Locust population L")
    plt.legend(loc="best", framealpha=0.95)
    plt.grid(True)
    plt.savefig(os.path.join(root, f"{plot_name}_L_populations_12yr.png"))
    plt.close()

    plt.figure(figsize=(10, 5))
    plt.plot(sol_12_0.t, sol_12_0.y[2], label="Simulated Grain (Eh = 0)", linewidth=2, color="tab:green")
    plt.plot(sol_12.t, sol_12.y[2], label="Simulated Grain (with Eh)", linewidth=2, alpha=0.7)
    plt.plot(np.arange(12), historical_scaled, "o-", label="Chicago Rice Data", color="red")
    plt.axvspan(4.0, 6.5, color="gray", alpha=0.2)
    plt.title("Ablation: hunting vs no hunting on 12-year window")
    plt.xlabel("Time (years)")
    plt.ylabel("Population Index")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(root, f"{plot_name}_ablation.png"))
    plt.close()


def metrics_for_report(p_lin):
    if len(p_lin) == 14:
        p_lin = expanded_params_lin(p_lin)
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4, S0, L0, G0, Eh = p_lin
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, b2]
    sol_b = solve_ivp(system, t_span, [S0, L0, G0], t_eval=t_eval, args=(0.0, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL)
    Gb = sol_b.y[2]
    scaling_factor = G0 / pre_shock_data[0]
    hist_s = positive_rice_production * scaling_factor
    sol_e = solve_ivp(system, t_span_12, [S0, L0, G0], t_eval=t_eval_12, args=(Eh, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL)
    sol_z = solve_ivp(system, t_span_12, [S0, L0, G0], t_eval=t_eval_12, args=(0.0, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL)
    ge = sol_e.y[2][::stepsPerYear]
    gz = sol_z.y[2][::stepsPerYear]
    from sklearn.metrics import r2_score

    r2_e = r2_score(hist_s, ge)
    r2_z = r2_score(hist_s, gz)
    return float(np.std(Gb)), r2_e, r2_z


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--export-best-checkpoint":
        export_best_checkpoint_scan()
        raise SystemExit(0)

    mega_start = time.time()
    report_idx = 2
    mega = 0
    best_cert_score = float("-inf")
    best_cert_p_lin = None
    best_cert_info = None

    while mega < MEGA_MAX and (time.time() - mega_start) < MEGA_TOTAL_WALL_S:
        mega += 1
        reset_solver_to_defaults()
        if mega % 12 == 0:
            working_bounds = [tuple(b) for b in log_bounds]
            print(f"[mega {mega}] reset working_bounds to full search box", file=sys.stderr)

        print(f"\n======== Mega iteration {mega}/{MEGA_MAX} (no early stop — always improving) ========\n", flush=True)
        print("Pass 1: Latin Hypercube", N_SAMPLES_PASS1, "samples")
        dur_pass1 = pass1_lhs(lhs_seed=42 + mega * 7919)
        print(f"Pass 1 done in {dur_pass1:.2f}s. Best loss so far: {best_score:.6f}")

        print("Pass 2: Differential Evolution")
        res, dur_pass2 = pass2_de(seed_base=10007 + mega * 97)
        print(f"Pass 2 done in {dur_pass2:.2f}s. DE reports fun={res.fun:.6f}")

        if best_params_log is None:
            print("No valid parameters found this mega — widening bounds and retrying.", file=sys.stderr)
            working_bounds = [tuple(b) for b in log_bounds]
            continue

        best_p_lin = log_to_lin(list(best_params_log))
        ok, info = check_requirements(best_p_lin)
        cs = certification_score(info)
        print(
            f"Global best check: loss={info['loss']:.6f} g_std={info['g_std']:.5f} "
            f"R2_eh={info['r2_eh']:.4f} R2_0={info['r2_0']:.4f} "
            f"crash_ratio={info['crash_mse_ratio_0_over_eh']:.3f} "
            f"narr_decl={info.get('narr_decline_rel', 0):.4f} narr_rec={info.get('narr_recovery_rel', 0):.4f} "
            f"hunt_S↓={info.get('hunt_suppresses_sparrows', False)} lag5r={info.get('baseline_lag5_corr', float('nan')):.3f} "
            f"ok={ok} cert_score={cs:.5f}",
            flush=True,
        )

        try:
            save_good_snapshot(best_p_lin, mega, info)
        except Exception as ex:
            print(f"good snapshot skipped: {ex}", file=sys.stderr)

        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        if ok and cs > best_cert_score:
            best_cert_score = cs
            best_cert_p_lin = expanded_params_lin(list(best_p_lin))
            best_cert_info = dict(info)
            write_certified_success(best_cert_p_lin, best_cert_info, mega, best_cert_score, ts=ts)
            plot_results(best_cert_p_lin, PLOT_TAG)
            print(f"[certified improvement] score={best_cert_score:.6f} mega={mega} — SUCCESS_REPORT.md updated", flush=True)

        report_idx += 1
        bsf = f"{best_cert_score:.6f}" if best_cert_score > float("-inf") else "none yet"
        rep = f"""# REPORT_ITERATION_{report_idx}.md
## Timestamp & Duration
- Completed: {ts}
- Mega iteration: {mega}
- Pass 1 (LHS): {dur_pass1:.2f}s
- Pass 2 (DE): {dur_pass2:.2f}s
- Elapsed since start: {time.time() - mega_start:.2f}s

## The Code Changes
- **Uninterrupted loop**: no exit on first success; narrative (decline during hunt, recovery after t=6.5), crash MSE ratio, penalties for sparrow suppression and baseline ~5y grain cycles.
- `SUCCESS_REPORT.md` **updates** when certification score improves.
- Certification `ok` requires: R² hist ≥ {SUCCESS_R2_HIST}, narrative mins, **mean sparrows lower with Eh than without on 4–6.5y** (min rel drop {HUNT_SPARROW_REL_DROP_MIN}), **30y Eh=0 grain lag-5 corr ≥ {BASELINE_LAG5_CORR_MIN}**.

## The Scores (global best this mega)
- Composite loss: {info['loss']:.6f}
- R² historical with Eh: {info['r2_eh']:.4f}
- R² historical with Eh=0: {info['r2_0']:.4f}
- Baseline oscillation (std G): {info['g_std']:.5f}
- Full criteria met: {ok}
- Certification score this mega: {cs:.6f}
- Best certified score so far: {bsf}
- Crash-window MSE ratio: {info['crash_mse_ratio_0_over_eh']:.4f}
- narr decline_rel / recovery_rel: {info.get('narr_decline_rel', 0):.5f} / {info.get('narr_recovery_rel', 0):.5f}
- hunt suppresses sparrows (4–6.5y): {info.get('hunt_suppresses_sparrows', False)} (rel drop {info.get('hunt_sparrow_rel_drop', float('nan')):.4f})
- baseline lag-5 grain corr: {info.get('baseline_lag5_corr', float('nan')):.4f}

## Visual Evidence
See `{OPT_LOG_ROOT}/{PLOT_TAG}_*.png` and `{OPT_LOG_ROOT}/checkpoints/`.

Per SPEC §5 (latest 12y snapshot): `plot_N.png` in this folder.

![plot_N](plot_N.png)
"""
        with open(os.path.join(OPT_LOG_ROOT, f"REPORT_ITERATION_{report_idx}.md"), "w") as f:
            f.write(rep)

        if STOP_WHEN_CERTIFIED and ok:
            done_msg = f"""# SPEC.md criteria satisfied

Mega iteration: {mega}
Timestamp: {ts}

`check_requirements` returned **ok** (R², loss, narrative, crash-window ratio, **hunting lowers sparrows on 4–6.5y vs no-hunt**, **regular 30y baseline grain ~5y cycles**).

See `SUCCESS_REPORT.md` and `{OPT_LOG_ROOT}/{PLOT_TAG}_*.png`.
"""
            with open(os.path.join(OPT_LOG_ROOT, "SPEC_CRITERIA_SATISFIED.md"), "w") as f:
                f.write(done_msg)
            print(
                f"[SPEC] All check_requirements criteria met — stopping mega loop (FAMINE_STOP_WHEN_CERTIFIED=1). "
                f"Wrote {OPT_LOG_ROOT}/SPEC_CRITERIA_SATISFIED.md",
                flush=True,
            )
            break

        if info["r2_eh"] < 0.88:
            pivot_working_bounds(mega)
        else:
            narrow_working_bounds(list(best_params_log))

    if best_params_log is None:
        raise SystemExit("Optimization produced no valid parameter vector.")

    best_p_lin = log_to_lin(list(best_params_log))
    _, final_info = check_requirements(best_p_lin)
    g_std, r2_eh, r2_0 = final_info["g_std"], final_info["r2_eh"], final_info["r2_0"]

    best_full = expanded_params_lin(list(best_p_lin))
    print(f"\nBest raw array (last DE, 16 with fixed a3, b4):\n[{', '.join(f'{x:.8e}' for x in best_full)}]")
    print(f"Baseline G std={g_std:.5f} | R2 hist (Eh)={r2_eh:.4f} | R2 hist (Eh=0)={r2_0:.4f}")

    if best_cert_p_lin is not None:
        plot_results(best_cert_p_lin, PLOT_TAG)
        print(f"Best certified score: {best_cert_score:.6f} (see SUCCESS_REPORT.md)", flush=True)
    else:
        plot_results(expanded_params_lin(list(best_p_lin)), PLOT_TAG)
        pending = f"""# Pending optimization (no certified solution yet or budget ended)

Last DE metrics:
- R² 12y with Eh: {r2_eh:.4f}
- R² 12y with Eh=0: {r2_0:.4f}
- Loss: {final_info['loss']:.6f}
- Mega iterations: {mega}

Re-run or extend `FAMINE_MEGA_WALL_S` / `FAMINE_MEGA_MAX`.
"""
        with open(os.path.join(OPT_LOG_ROOT, "PENDING_RUN.md"), "w") as f:
            f.write(pending)
