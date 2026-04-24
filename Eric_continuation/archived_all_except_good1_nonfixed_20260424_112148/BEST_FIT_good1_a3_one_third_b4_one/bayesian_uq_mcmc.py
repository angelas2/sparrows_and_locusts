#!/usr/bin/env python3
"""
Bayesian UQ for the famine ODE (grain observation), following
LLM_Bayesian_UQ_ODE_Protocol.md: log-normal-ish priors on log10(params),
Gaussian likelihood on annual grain vs Chicago rice (scaled), unknown sigma;
emcee ensemble MCMC; trace, corner, posterior predictive plots.

Run from repo root:  ./venv/bin/python BEST_FIT_good1_a3_one_third_b4_one/bayesian_uq_mcmc.py
"""
from __future__ import annotations

import json
import os
import sys
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import solve_ivp

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, _REPO)

import emcee
import famine_model as fm

warnings.filterwarnings("ignore")

BEST_JSON = os.path.join(_HERE, "best_fit.json")
OUT_PREFIX = os.path.join(_HERE, "mcmc_uq")
NWALKERS = 32  # >= 2 * ndim for stretch move (ndim=15)
NSTEPS = 55
NBURN = 18
T_EVAL_MCMC = np.linspace(0.0, 12.0, 12 * 8 + 1)
PRIOR_SIG_LOG = 0.14
PRIOR_CENTER_LOGSIG = -1.55
PRIOR_SIG_LOGSIG = 0.38


def load_center() -> tuple[np.ndarray, np.ndarray, float]:
    with open(BEST_JSON, encoding="utf-8") as f:
        d = json.load(f)
    p_log = np.array(d["params_log_14"], dtype=float)
    pl = d["params_lin_full"]
    G0 = float(pl[14])
    return p_log, np.array(pl, dtype=float), G0


def observation_vector(G0: float) -> tuple[np.ndarray, np.ndarray]:
    scaling = G0 / fm.pre_shock_data[0]
    y = fm.positive_rice_production[:12] * scaling
    t = np.arange(12, dtype=float)
    return t, y


def simulate_grain_at_integers(p_log_14: np.ndarray) -> np.ndarray | None:
    p_lin = [10 ** float(x) for x in p_log_14]
    full = fm.expanded_params_lin(p_lin)
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, _a3, b2, _b4, S0, L0, G0, Eh = full
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, b2]
    try:
        sol = solve_ivp(
            fm.system,
            (0.0, 12.0),
            [S0, L0, G0],
            t_eval=T_EVAL_MCMC,
            args=(Eh, *sys_params),
            method="LSODA",
            atol=5e-5,
            rtol=5e-5,
        )
    except Exception:
        return None
    if not sol.success or sol.status == 1:
        return None
    t_obs = np.arange(12, dtype=float)
    g = np.interp(t_obs, sol.t, sol.y[2])
    if not np.all(np.isfinite(g)):
        return None
    return g


def log_prior(theta: np.ndarray) -> float:
    """Weakly informative Gaussian on log10 dynamic params + log10 sigma (relative scale)."""
    if theta.shape[0] != 15:
        return -np.inf
    p_log = theta[:-1]
    for i, (lo, hi) in enumerate(fm.log_bounds):
        if not (lo - 1e-6 <= p_log[i] <= hi + 1e-6):
            return -np.inf
    logsig = theta[-1]
    if logsig < -4.0 or logsig > 1.0:
        return -np.inf
    d = p_log - _CENTER_LOG
    pr = -0.5 * np.sum((d / PRIOR_SIG_LOG) ** 2)
    pr += -0.5 * ((logsig - PRIOR_CENTER_LOGSIG) / PRIOR_SIG_LOGSIG) ** 2
    return float(pr)


def log_likelihood(theta: np.ndarray, y: np.ndarray) -> float:
    pred = simulate_grain_at_integers(theta[:-1])
    if pred is None:
        return -np.inf
    sigma = 10 ** float(theta[-1])
    if sigma <= 0:
        return -np.inf
    ref = max(float(np.mean(y)), 1e-12)
    yn = y / ref
    pn = pred / ref
    resid = (pn - yn) / sigma
    n = len(y)
    ll = -0.5 * n * np.log(2 * np.pi * sigma**2) - 0.5 * np.sum(resid**2)
    return float(ll)


def log_probability(theta: np.ndarray, y: np.ndarray) -> float:
    lp = log_prior(theta)
    if not np.isfinite(lp):
        return -np.inf
    ll = log_likelihood(theta, y)
    if not np.isfinite(ll):
        return -np.inf
    return lp + ll


_CENTER_LOG, _PL_FULL, _G0 = load_center()
_T_OBS, _Y_OBS = observation_vector(_G0)


def main() -> int:
    ndim = 15
    pos = []
    rng = np.random.default_rng(42)
    for _ in range(NWALKERS):
        jitter = rng.normal(0, 0.012, size=14)
        th = np.concatenate([_CENTER_LOG + jitter, [PRIOR_CENTER_LOGSIG + rng.normal(0, 0.05)]])
        pos.append(th)
    pos = np.array(pos)

    sampler = emcee.EnsembleSampler(
        NWALKERS,
        ndim,
        log_probability,
        args=(_Y_OBS,),
        vectorize=False,
    )
    sampler.run_mcmc(pos, NSTEPS, progress=False)
    chain = sampler.get_chain(discard=NBURN, flat=False)
    flat = sampler.get_chain(discard=NBURN, flat=True)

    np.save(OUT_PREFIX + "_chain_flat.npy", flat)
    names = [
        r"$\log_{10}\lambda$",
        r"$\log_{10}a_2$",
        r"$\log_{10}b_1$",
        r"$\log_{10}b_3$",
        r"$\log_{10}b_5$",
        r"$\log_{10}c_1$",
        r"$\log_{10}c_2$",
        r"$\log_{10}r_g$",
        r"$\log_{10}K_\ell$",
        r"$\log_{10}b_2$",
        r"$\log_{10}S_0$",
        r"$\log_{10}L_0$",
        r"$\log_{10}G_0$",
        r"$\log_{10}E_h$",
        r"$\log_{10}\sigma$",
    ]

    # Trace (first 6 + sigma)
    fig, axes = plt.subplots(7, 1, figsize=(9, 8), sharex=True)
    for i, ax in enumerate(axes):
        idx = i if i < 6 else 14
        ax.plot(chain[:, :, idx], color="k", alpha=0.25, lw=0.6)
        ax.set_ylabel(names[idx], fontsize=8)
    axes[-1].set_xlabel("step")
    fig.suptitle(r"MCMC traces (subset + $\log_{10}\sigma$)")
    fig.tight_layout()
    fig.savefig(OUT_PREFIX + "_traces.png", dpi=120)
    plt.close(fig)

    try:
        import corner

        fig = corner.corner(
            flat[:, [0, 1, 2, 3, 4, 5, 14]],
            labels=[names[i] for i in [0, 1, 2, 3, 4, 5, 14]],
            quantiles=[0.16, 0.5, 0.84],
            show_titles=True,
            title_fmt=".3f",
        )
        fig.savefig(OUT_PREFIX + "_corner_subset.png", dpi=120)
        plt.close(fig)
    except Exception as ex:
        print("corner subset failed:", ex, file=sys.stderr)

    # Posterior predictive on grain
    rng = np.random.default_rng(7)
    idxs = rng.choice(len(flat), size=min(48, len(flat)), replace=False)
    curves = []
    for th in flat[idxs]:
        g = simulate_grain_at_integers(th[:-1])
        if g is not None:
            curves.append(g / max(np.mean(_Y_OBS), 1e-12))
    if curves:
        curves = np.array(curves)
        lo = np.percentile(curves, 5, axis=0)
        hi = np.percentile(curves, 95, axis=0)
        med = np.median(curves, axis=0)
        yn = _Y_OBS / max(np.mean(_Y_OBS), 1e-12)
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.fill_between(_T_OBS, lo, hi, alpha=0.35, label="90% posterior predictive (grain)")
        ax.plot(_T_OBS, med, "b-", lw=2, label="Posterior median")
        ax.plot(_T_OBS, yn, "ro", ms=5, label="Observed (scaled grain)")
        ax.set_xlabel("Year index (1954+k)")
        ax.set_ylabel(r"$G / \mathrm{mean}(y)$")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_title("Posterior predictive check (normalized grain)")
        fig.tight_layout()
        fig.savefig(OUT_PREFIX + "_ppc_grain.png", dpi=120)
        plt.close(fig)

    summary = {
        "nwalkers": NWALKERS,
        "nsteps": NSTEPS,
        "nburn": NBURN,
        "ndim": ndim,
        "mean_acceptance": float(np.mean(sampler.acceptance_fraction)),
        "flat_chain_shape": list(flat.shape),
        "output_files": [
            OUT_PREFIX + "_chain_flat.npy",
            OUT_PREFIX + "_traces.png",
            OUT_PREFIX + "_corner_subset.png",
            OUT_PREFIX + "_ppc_grain.png",
        ],
    }
    with open(OUT_PREFIX + "_run_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("Wrote:", OUT_PREFIX + "_*")
    print("mean acceptance", summary["mean_acceptance"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
