#!/usr/bin/env python3
"""
Bayesian UQ for good #1 with NON-FIXED sparrow/locust death rates (a3, b4 free in
the 16-parameter vector). ODE RHS matches famine_model but uses a3, b4 from the
proposal (not famine_model.FIXED_A3/FIXED_B4).

Protocol: LLM_Bayesian_UQ_ODE_Protocol.md (priors, Gaussian likelihood, emcee,
traces, corner, PPC).

Run from repo root:
  ./venv/bin/python GOOD1_nonfixed_death_rates_Bayesian_bundle/bayesian_uq_mcmc.py
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

_BUNDLE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_BUNDLE)
sys.path.insert(0, _REPO)

import emcee
import famine_model as fm

warnings.filterwarnings("ignore")

CK = os.path.join(_BUNDLE, "checkpoint.json")
OUT_PREFIX = os.path.join(_BUNDLE, "mcmc_uq")
NWALKERS = 40  # >= 2 * ndim, ndim=17
NSTEPS = 220
NBURN = 70
T_EVAL_MCMC = np.linspace(0.0, 12.0, 12 * 8 + 1)
PRIOR_SIG_LOG = 0.13
PRIOR_CENTER_LOGSIG = -1.55
PRIOR_SIG_LOGSIG = 0.38

# Extra log10 bounds for a3, b4 (not in famine_model.log_bounds)
LOG_BOUNDS_A3 = (-1.35, 0.35)
LOG_BOUNDS_B4 = (-0.55, 1.25)


def rhs(t, y, Eh, lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4):
    S, L, G = y

    def f_locust(Lv):
        return b1 + (b2 * Lv**2) / (b3**2 + Lv**2)

    current_Eh = Eh if 4.0 <= t <= 6.5 else 0.0
    dS = (lam * S * L) / (K_l + L) + (a2 * G * S) - (a3 * S) - (current_Eh * S)
    dL = f_locust(L) * L - (b4 * L) - (b5 * S * L)
    dG = (r_g * (1 - G)) - (c1 * G * S) - (c2 * G * L) - (1.0 * G)
    return [dS, dL, dG]


def load_checkpoint():
    with open(CK, encoding="utf-8") as f:
        d = json.load(f)
    return np.array(d["params_log"], dtype=float), np.array(d["params_lin"], dtype=float)


def observation_vector(G0: float):
    scaling = G0 / fm.pre_shock_data[0]
    y = fm.positive_rice_production[:12] * scaling
    t = np.arange(12, dtype=float)
    return t, y


def simulate_grain_at_integers(p_log_16: np.ndarray) -> np.ndarray | None:
    p_lin = [10 ** float(x) for x in p_log_16]
    (
        lam,
        a2,
        b1,
        b3,
        b5,
        c1,
        c2,
        r_g,
        K_l,
        a3,
        b2,
        b4,
        S0,
        L0,
        G0,
        Eh,
    ) = p_lin

    def fun(t, y):
        return rhs(t, y, Eh, lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4)

    try:
        sol = solve_ivp(
            fun,
            (0.0, 12.0),
            [S0, L0, G0],
            t_eval=T_EVAL_MCMC,
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
    if not np.all(np.isfinite(g)) or np.min(g) < -1e-6 or np.max(g) > 1.5:
        return None
    return g


def log_prior(theta: np.ndarray) -> float:
    if theta.shape[0] != 17:
        return -np.inf
    p_log = theta[:-1]
    # First 9: same order as famine log_bounds[:9]
    for i in range(9):
        lo, hi = fm.log_bounds[i]
        if not (lo - 1e-6 <= p_log[i] <= hi + 1e-6):
            return -np.inf
    # indices 9,10 in 16-vector are a3, b2 — famine log_bounds[9] is b2
    lo, hi = fm.log_bounds[9]
    if not (lo - 1e-6 <= p_log[10] <= hi + 1e-6):
        return -np.inf
    # a3 at index 9
    if not (LOG_BOUNDS_A3[0] - 1e-6 <= p_log[9] <= LOG_BOUNDS_A3[1] + 1e-6):
        return -np.inf
    # b4 at index 11
    if not (LOG_BOUNDS_B4[0] - 1e-6 <= p_log[11] <= LOG_BOUNDS_B4[1] + 1e-6):
        return -np.inf
    # S0, L0, G0, Eh at 12..15 map to famine log_bounds 10..13
    for j, k in enumerate([12, 13, 14, 15]):
        lo, hi = fm.log_bounds[10 + j]
        if not (lo - 1e-6 <= p_log[k] <= hi + 1e-6):
            return -np.inf

    logsig = theta[-1]
    if logsig < -4.0 or logsig > 1.0:
        return -np.inf

    d = p_log - _CENTER_LOG16
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


_CENTER_LOG16, _PL_LIN = load_checkpoint()
_G0 = float(_PL_LIN[14])
_T_OBS, _Y_OBS = observation_vector(_G0)


def main() -> int:
    ndim = 17
    rng = np.random.default_rng(20250424)
    pos = []
    for _ in range(NWALKERS):
        jitter = rng.normal(0, 0.01, size=16)
        th = np.concatenate([_CENTER_LOG16 + jitter, [PRIOR_CENTER_LOGSIG + rng.normal(0, 0.04)]])
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

    flat = sampler.get_chain(discard=NBURN, flat=True)
    chain = sampler.get_chain(discard=NBURN, flat=False)
    np.save(OUT_PREFIX + "_chain_flat.npy", flat)

    names = [
        r"$\log\lambda$",
        r"$\log a_2$",
        r"$\log b_1$",
        r"$\log b_3$",
        r"$\log b_5$",
        r"$\log c_1$",
        r"$\log c_2$",
        r"$\log r_g$",
        r"$\log K_\ell$",
        r"$\log a_3$",
        r"$\log b_2$",
        r"$\log b_4$",
        r"$\log S_0$",
        r"$\log L_0$",
        r"$\log G_0$",
        r"$\log E_h$",
        r"$\log\sigma$",
    ]

    # Trace plots: all ndim continuous unknowns (16 log10 ODE/IC params + log10 sigma)
    nrows, ncols = 6, 3
    fig, axes = plt.subplots(nrows, ncols, figsize=(12, 22), sharex=True)
    axes_flat = axes.flatten()
    for idx in range(ndim):
        ax = axes_flat[idx]
        ax.plot(chain[:, :, idx], color="k", alpha=0.18, lw=0.48)
        ax.set_ylabel(names[idx], fontsize=7)
        ax.tick_params(axis="both", labelsize=6)
        ax.grid(True, alpha=0.22)
    for j in range(ndim, len(axes_flat)):
        axes_flat[j].set_visible(False)
    for idx in (12, 13, 14, 15, 16):
        axes_flat[idx].set_xlabel("MCMC step", fontsize=7)
    fig.suptitle(
        r"MCMC traces — all unknowns ($\log_{10}$ of $\lambda,a_2,b_1,\ldots,E_h$ + $\log_{10}\sigma$)",
        fontsize=11,
        y=0.998,
    )
    fig.subplots_adjust(left=0.12, right=0.98, top=0.97, bottom=0.05, hspace=0.38, wspace=0.28)
    fig.savefig(OUT_PREFIX + "_traces.png", dpi=130)
    plt.close(fig)

    try:
        import corner

        fig = corner.corner(
            flat[:, [9, 11, 16]],
            labels=[names[9], names[11], names[16]],
            quantiles=[0.16, 0.5, 0.84],
            show_titles=True,
            title_fmt=".3f",
        )
        fig.savefig(OUT_PREFIX + "_corner_a3_b4_sigma.png", dpi=120)
        plt.close(fig)
    except Exception as ex:
        print("corner failed:", ex, file=sys.stderr)

    rng = np.random.default_rng(11)
    idxs = rng.choice(len(flat), size=min(40, len(flat)), replace=False)
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
        ax.fill_between(_T_OBS, lo, hi, alpha=0.35, label="90% posterior predictive")
        ax.plot(_T_OBS, med, "b-", lw=2, label="Posterior median")
        ax.plot(_T_OBS, yn, "ro", ms=5, label="Observed (normalized)")
        ax.set_xlabel("Year index")
        ax.set_ylabel(r"$G / \mathrm{mean}(y)$")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_title("Posterior predictive: grain (good #1, free $a_3,b_4$)")
        fig.tight_layout()
        fig.savefig(OUT_PREFIX + "_ppc_grain.png", dpi=120)
        plt.close(fig)

    summary = {
        "checkpoint": CK,
        "nwalkers": NWALKERS,
        "nsteps": NSTEPS,
        "nburn": NBURN,
        "ndim": ndim,
        "mean_acceptance": float(np.mean(sampler.acceptance_fraction)),
        "flat_chain_shape": list(flat.shape),
        "note": "a3, b4 vary in ODE; not tied to famine_model.FIXED_A3/FIXED_B4.",
    }
    with open(OUT_PREFIX + "_run_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("Wrote", OUT_PREFIX + "_*")
    print("mean acceptance", summary["mean_acceptance"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
