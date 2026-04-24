import numpy as np
import sys
import os
import json
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
# Scale rice to [0, G0] with max historical point = G0 (≤1 when G0≤1). Replaces G0/pre_shock[0].
RICE_MAX = float(np.max(positive_rice_production))

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
PLOT_TAG = "final_g07"
CHECKPOINT_ROOT = os.path.join("optimization_logs", "checkpoints")
CHECKPOINT_FULL_PLOT_MAX_LOSS = 3.0
CHECKPOINT_SAVE_MAX_LOSS = 2500.0
DE_ROUNDS = 3

PASS1_SPEC_SECONDS = 30.0
PASS1_TOTAL_MAX_S = 240.0
DE_ROUND_MAX_S = 420.0
EVAL_TOTAL_MAX_S = 22.0
speed_tier = 0

SUCCESS_R2_HIST = float(os.environ.get("FAMINE_SUCCESS_R2", "0.848"))
SUCCESS_G_STD = 0.022
SUCCESS_LOSS_MAX = 0.58
SUCCESS_R2_MARGIN = 0.035
CRASH_WINDOW_MSE_RATIO_MIN = float(os.environ.get("FAMINE_CRASH_RATIO_MIN", "1.18"))
NARRATIVE_DECLINE_REL_MIN = 0.004
NARRATIVE_RECOVERY_REL_MIN = 0.006
NARRATIVE_PEN_W = 120.0
MEGA_MAX = int(os.environ.get("FAMINE_MEGA_MAX", "10000"))
MEGA_TOTAL_WALL_S = float(os.environ.get("FAMINE_MEGA_WALL_S", str(30 * 24 * 3600)))
GOOD_R2_SAVE = 0.72
GOOD_LOSS_SAVE = 1.25

os.makedirs("optimization_logs", exist_ok=True)
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
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4 = params
    current_Eh = Eh if 4.0 <= t <= 6.5 else 0.0

    def f(Lv):
        return b1 + (b2 * Lv**2) / (b3**2 + Lv**2)

    dS = (lam * S * L) / (K_l + L) + (a2 * G * S) - (a3 * S) - (current_Eh * S)
    dL = f(L) * L - (b4 * L) - (b5 * S * L)
    dG = (r_g * (1 - G)) - (c1 * G * S) - (c2 * G * L) - (1.0 * G)
    return [dS, dL, dG]


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
    (-2, -0.3),
    (-2, 1),
    (-2, 0.5),
    (-0.5, 1.5),
    (0.5, 2),
    (-0.22, -0.06),
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
        "params_lin": [float(x) for x in p_lin],
    }
    with open(os.path.join(ck_dir, "checkpoint.json"), "w") as f:
        json.dump(meta, f, indent=2)
    np.save(os.path.join(ck_dir, "params_log.npy"), np.array(p_log, dtype=float))
    if loss <= CHECKPOINT_FULL_PLOT_MAX_LOSS:
        plot_prefix = os.path.join(os.path.relpath(ck_dir, "optimization_logs"), "plot")
        plot_results(p_lin, plot_prefix)
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


def crash_window_hunt_explains(p_lin):
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4, S0, L0, G0, Eh = p_lin
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4]
    scaling_factor = G0 / RICE_MAX
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


def check_requirements(p_lin):
    p_log = lin_to_log(p_lin)
    loss = float(evaluate_params(p_log, track_best=False))
    g_std, r2_e, r2_z = metrics_for_report(p_lin)
    explains, mce, mc0, ratio = crash_window_hunt_explains(p_lin)
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4, S0, L0, G0, Eh = p_lin
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4]
    sol_e = solve_ivp(
        system, t_span_12, [S0, L0, G0], t_eval=t_eval_12,
        args=(Eh, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL,
    )
    narr = narrative_grain_shape(sol_e)
    ok = (
        loss <= SUCCESS_LOSS_MAX
        and g_std >= SUCCESS_G_STD
        and r2_e >= SUCCESS_R2_HIST
        and (r2_e - r2_z) >= SUCCESS_R2_MARGIN
        and explains
        and narr["decline_ok"]
        and narr["recovery_ok"]
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
        **{f"narr_{k}": v for k, v in narr.items()},
    }
    return ok, out


def certification_score(info):
    return (
        float(info["r2_eh"])
        - 0.14 * min(float(info["loss"]), 3.0)
        + 2.2 * min(float(info.get("narr_recovery_rel", 0.0)), 0.12)
        + 1.1 * min(float(info.get("narr_decline_rel", 0.0)), 0.12)
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
    side = os.path.join("optimization_logs", "best_certified.json")
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


def save_good_snapshot(p_lin, mega, info):
    loss = info["loss"]
    r2_e = info["r2_eh"]
    if loss > GOOD_LOSS_SAVE and r2_e < GOOD_R2_SAVE:
        return
    tag = f"good_mega{mega:04d}_r2_{r2_e:.4f}_loss_{loss:.4f}_{int(time.time())}"
    d = os.path.join(CHECKPOINT_ROOT, tag)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "good_snapshot.json"), "w") as f:
        json.dump({**info, "mega": mega, "params_lin": [float(x) for x in p_lin]}, f, indent=2)
    np.save(os.path.join(d, "params_lin.npy"), np.array(p_lin, dtype=float))
    plot_prefix = os.path.join(os.path.relpath(d, "optimization_logs"), "plot")
    plot_results(p_lin, plot_prefix)
    print(f"[good snapshot] -> {d}/", file=sys.stderr)


def evaluate_params(p_log, track_best=True):
    global best_score, best_params_log
    p = log_to_lin(p_log)
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4, S0, L0, G0, Eh = p
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4]

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

        scaling_factor = G0 / RICE_MAX
        target_scaled = repeated_data_30 * scaling_factor

        sim_range = float(np.max(sim_grains_base) - np.min(sim_grains_base))
        target_range = float(np.max(target_scaled) - np.min(target_scaled))
        if target_range > 1e-12 and sim_range < (target_range * 0.35):
            penalty += (target_range * 0.35 - sim_range) * 2e5

        g_std = float(np.std(G_osc))
        if g_std < 0.02:
            penalty += (0.02 - g_std) * 5e5

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

        g_peak = max(
            float(np.max(G_osc)),
            float(np.max(sol_hist.y[2])),
            float(np.max(sol_hist0.y[2])),
        )
        if g_peak > 1.0:
            penalty += (g_peak - 1.0) * 2.0e6

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
        if gap < 0.012:
            penalty += (0.012 - gap) * 1.2e4

        combined = 0.22 * mse_base + 0.78 * mse_hist_eh
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
                "SPEC: Pass 1 exceeded 30s after 10% completion — tightening tolerances and ending LHS early"
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


def plot_results(best_params, plot_name="plot"):
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4, S0, L0, G0, Eh = best_params
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4]

    sol_30 = solve_ivp(
        system, t_span, [S0, L0, G0], t_eval=t_eval,
        args=(0.0, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL,
    )
    scaling_factor = G0 / RICE_MAX
    target_scaled = repeated_data_30 * scaling_factor

    plt.figure(figsize=(10, 5))
    plt.plot(sol_30.t, sol_30.y[2], label="Simulated Grain (Natural Oscillation)", linewidth=2)
    plt.plot(np.arange(30), target_scaled, "o--", label="Synthetic 30-Year Target", color="red", alpha=0.6)
    plt.title("30-Year Natural Oscillation Fit (Pre-Shock Baseline)")
    plt.xlabel("Time (years)")
    plt.ylabel("Population Index")
    plt.legend()
    plt.grid(True)
    plt.savefig(f"optimization_logs/{plot_name}_30yr.png")
    plt.close()

    sol_12 = solve_ivp(
        system, t_span_12, [S0, L0, G0], t_eval=t_eval_12,
        args=(Eh, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL,
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
    plt.savefig(f"optimization_logs/{plot_name}_12yr.png")
    plt.savefig("optimization_logs/plot_N.png")
    plt.close()

    sol_12_0 = solve_ivp(
        system, t_span_12, [S0, L0, G0], t_eval=t_eval_12,
        args=(0.0, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL,
    )
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
    plt.savefig(f"optimization_logs/{plot_name}_ablation.png")
    plt.close()


def metrics_for_report(p_lin):
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4, S0, L0, G0, Eh = p_lin
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4]
    sol_b = solve_ivp(system, t_span, [S0, L0, G0], t_eval=t_eval, args=(0.0, *sys_params), method="LSODA", atol=ATOL, rtol=RTOL)
    Gb = sol_b.y[2]
    scaling_factor = G0 / RICE_MAX
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
            best_cert_p_lin = list(best_p_lin)
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
- **Uninterrupted loop**: no exit on first success; narrative (decline during hunt, recovery after t=6.5), crash MSE ratio, hunting-gap penalty.
- `SUCCESS_REPORT.md` **updates** when certification score improves.
- R² hist ≥ {SUCCESS_R2_HIST}, narrative mins: decline_rel ≥ {NARRATIVE_DECLINE_REL_MIN}, recovery_rel ≥ {NARRATIVE_RECOVERY_REL_MIN}.

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

## Visual Evidence
See `optimization_logs/{PLOT_TAG}_*.png` and `optimization_logs/checkpoints/`.
"""
        with open(f"optimization_logs/REPORT_ITERATION_{report_idx}.md", "w") as f:
            f.write(rep)

        if info["r2_eh"] < 0.85:
            pivot_working_bounds(mega)
        else:
            narrow_working_bounds(list(best_params_log))

    if best_params_log is None:
        raise SystemExit("Optimization produced no valid parameter vector.")

    best_p_lin = log_to_lin(list(best_params_log))
    _, final_info = check_requirements(best_p_lin)
    g_std, r2_eh, r2_0 = final_info["g_std"], final_info["r2_eh"], final_info["r2_0"]

    print(f"\nBest raw array (last DE):\n[{', '.join(f'{x:.8e}' for x in best_p_lin)}]")
    print(f"Baseline G std={g_std:.5f} | R2 hist (Eh)={r2_eh:.4f} | R2 hist (Eh=0)={r2_0:.4f}")

    if best_cert_p_lin is not None:
        plot_results(best_cert_p_lin, PLOT_TAG)
        print(f"Best certified score: {best_cert_score:.6f} (see SUCCESS_REPORT.md)", flush=True)
    else:
        plot_results(best_p_lin, PLOT_TAG)
        pending = f"""# Pending optimization (no certified solution yet or budget ended)

Last DE metrics:
- R² 12y with Eh: {r2_eh:.4f}
- R² 12y with Eh=0: {r2_0:.4f}
- Loss: {final_info['loss']:.6f}
- Mega iterations: {mega}

Re-run or extend `FAMINE_MEGA_WALL_S` / `FAMINE_MEGA_MAX`.
"""
        with open(os.path.join("optimization_logs", "PENDING_RUN.md"), "w") as f:
            f.write(pending)
