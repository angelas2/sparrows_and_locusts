#!/usr/bin/env python3
"""
Local sensitivity of simulated annual grain G(t=k), k=0..11, to each of the 16
log10 parameters in good #1 checkpoint (non-fixed a3, b4 ODE).

Method: central finite differences on log10(parameters):
  J[k,j] ≈ ∂G_k / ∂(log10 p_j)

Also writes elasticity-style columns:
  E[k,j] = (p_j / G_k) * ∂G_k/∂p_j = J[k,j] / (G_k * ln 10)
  (when |G_k| is tiny, clip denominator for display)

Run from repo root:
  ./venv/bin/python GOOD1_nonfixed_death_rates_Bayesian_bundle/sensitivity_grain.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

_BUNDLE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_BUNDLE)
sys.path.insert(0, _REPO)


def _load_buq():
    path = os.path.join(_BUNDLE, "bayesian_uq_mcmc.py")
    spec = importlib.util.spec_from_file_location("buq", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


PARAM_NAMES = [
    r"$\log_{10}\lambda$",
    r"$\log_{10}a_2$",
    r"$\log_{10}b_1$",
    r"$\log_{10}b_3$",
    r"$\log_{10}b_5$",
    r"$\log_{10}c_1$",
    r"$\log_{10}c_2$",
    r"$\log_{10}r_g$",
    r"$\log_{10}K_\ell$",
    r"$\log_{10}a_3$",
    r"$\log_{10}b_2$",
    r"$\log_{10}b_4$",
    r"$\log_{10}S_0$",
    r"$\log_{10}L_0$",
    r"$\log_{10}G_0$",
    r"$\log_{10}E_h$",
]

PARAM_KEYS = [
    "lam",
    "a2",
    "b1",
    "b3",
    "b5",
    "c1",
    "c2",
    "r_g",
    "K_l",
    "a3",
    "b2",
    "b4",
    "S0",
    "L0",
    "G0",
    "Eh",
]


def main() -> int:
    buq = _load_buq()
    p_log, _p_lin = buq.load_checkpoint()
    p_log = np.array(p_log, dtype=float)

    eps = float(os.environ.get("GRAIN_SENS_EPS_LOG10", "0.018"))
    simulate = buq.simulate_grain_at_integers
    G_base = simulate(p_log)
    if G_base is None:
        print("Baseline simulate failed", file=sys.stderr)
        return 1

    n_t, n_p = 12, 16
    J = np.full((n_t, n_p), np.nan, dtype=float)
    LN10 = np.log(10.0)

    for j in range(n_p):
        pp = p_log.copy()
        pp[j] += eps
        gp = simulate(pp)
        pm = p_log.copy()
        pm[j] -= eps
        gm = simulate(pm)
        if gp is None or gm is None:
            continue
        J[:, j] = (gp - gm) / (2.0 * eps)

    # Elasticity (fractional change in G per fractional change in p): J/(G*ln10)
    Gsafe = np.where(np.abs(G_base) > 1e-12, G_base, np.sign(G_base) * 1e-12 + 1e-12)
    E = J / (Gsafe[:, None] * LN10)

    out_csv = os.path.join(_BUNDLE, "sensitivity_grain_dG_dlog10p.csv")
    header = "year_index," + ",".join(PARAM_KEYS)
    with open(out_csv, "w", encoding="utf-8") as f:
        f.write(header + "\n")
        for k in range(n_t):
            row = [str(k)] + [f"{J[k, j]:.8e}" if np.isfinite(J[k, j]) else "" for j in range(n_p)]
            f.write(",".join(row) + "\n")

    out_el = os.path.join(_BUNDLE, "sensitivity_grain_elasticity.csv")
    with open(out_el, "w", encoding="utf-8") as f:
        f.write("year_index," + ",".join(f"elasticity_{k}" for k in PARAM_KEYS) + "\n")
        for k in range(n_t):
            row = [str(k)] + [f"{E[k, j]:.8e}" if np.isfinite(E[k, j]) else "" for j in range(n_p)]
            f.write(",".join(row) + "\n")

    # Heatmap: normalized absolute Jacobian per time row (shows relative drivers each year)
    A = np.nan_to_num(np.abs(J), nan=0.0)
    row_max = np.maximum(A.max(axis=1, keepdims=True), 1e-30)
    Z = A / row_max

    fig, ax = plt.subplots(figsize=(11, 5.2))
    im = ax.imshow(Z, aspect="auto", cmap="magma", vmin=0, vmax=1)
    ax.set_xticks(np.arange(n_p))
    ax.set_xticklabels(PARAM_KEYS, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(np.arange(n_t))
    ax.set_yticklabels([str(k) for k in range(n_t)])
    ax.set_xlabel("Parameter (perturbation in log10)")
    ax.set_ylabel("Year index k (grain G(k))")
    ax.set_title(
        r"Grain sensitivity: $| \partial G_k / \partial \log_{10} p_j |$ "
        r"(rows normalized to max $=1$)"
    )
    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02, label="relative |∂G/∂log10 p|")
    fig.tight_layout()
    fig.savefig(os.path.join(_BUNDLE, "sensitivity_grain_heatmap.png"), dpi=140)
    plt.close(fig)

    # Tornado at mid-crash year (k=7) using |elasticity|
    k = int(os.environ.get("GRAIN_SENS_TORNADO_YEAR", "7"))
    k = max(0, min(11, k))
    mag = np.nan_to_num(np.abs(E[k]), nan=0.0)
    order = np.argsort(mag)[::-1]
    fig, ax = plt.subplots(figsize=(8, 5))
    y = np.arange(n_p)[::-1]
    ax.barh(y, mag[order], color="steelblue", alpha=0.85)
    labels = [PARAM_KEYS[i] for i in order]
    ax.set_yticks(np.arange(n_p))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel(r"$|E_{k,j}|$ = $| (p_j/G_k)\, \partial G_k/\partial p_j |$" + f" at k={k}")
    ax.set_title(f"Grain sensitivity tornado at year k={k} (sorted by |elasticity|)")
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(_BUNDLE, "sensitivity_grain_tornado.png"), dpi=140)
    plt.close(fig)

    meta = {
        "checkpoint": buq.CK,
        "eps_log10": eps,
        "tornado_year_index": k,
        "outputs": [
            out_csv,
            out_el,
            os.path.join(_BUNDLE, "sensitivity_grain_heatmap.png"),
            os.path.join(_BUNDLE, "sensitivity_grain_tornado.png"),
        ],
    }
    with open(os.path.join(_BUNDLE, "sensitivity_grain_run.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("Wrote sensitivity_grain_*.csv/png/json under", _BUNDLE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
