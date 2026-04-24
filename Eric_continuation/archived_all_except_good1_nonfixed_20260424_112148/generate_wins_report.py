#!/usr/bin/env python3
"""Build REPORT.txt and S/L population plots for each subfolder under Wins (assigned)."""
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import solve_ivp

PARAM_NAMES = [
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

YEARS_CAL = np.arange(1954, 1966)


def system(t, y, Eh, *params):
    S, L, G = y
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4 = params

    def f(Lv):
        return b1 + (b2 * Lv**2) / (b3**2 + Lv**2)

    current_Eh = Eh if 4.0 <= t <= 6.5 else 0.0
    dS = (lam * S * L) / (K_l + L) + (a2 * G * S) - (a3 * S) - (current_Eh * S)
    dL = f(L) * L - (b4 * L) - (b5 * S * L)
    dG = (r_g * (1 - G)) - (c1 * G * S) - (c2 * G * L) - (1.0 * G)
    return [dS, dL, dG]


def load_params_lin(folder):
    for name in ("checkpoint.json", "good_snapshot.json"):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            pl = data.get("params_lin")
            if pl is not None and len(pl) == 16:
                return data, pl
    return None, None


def unpack(pl):
    lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4, S0, L0, G0, Eh = pl
    sys_params = [lam, a2, b1, b3, b5, c1, c2, r_g, K_l, a3, b2, b4]
    return sys_params, S0, L0, G0, Eh


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    subdirs = sorted(
        [
            os.path.join(root, name)
            for name in os.listdir(root)
            if os.path.isdir(os.path.join(root, name)) and not name.startswith(".")
        ]
    )
    if not subdirs:
        print("No subfolders found.", file=sys.stderr)
        sys.exit(1)

    steps = 30
    t_eval_30 = np.linspace(0, 30, steps * 30)
    t_eval_12 = np.linspace(0, 12, steps * 12)
    atol = rtol = 1e-3

    report_lines = [
        "Famine model — assigned wins: parameters and figures",
        "=" * 72,
        "",
        "Dynamics: S = sparrows, L = locusts, G = grain (not plotted here).",
        "30-year plots: baseline with Eh = 0 for full period.",
        "12-year plots: historical window with hunting on S for 4.0 ≤ t ≤ 6.5 years.",
        "",
    ]

    for folder in subdirs:
        label = os.path.basename(folder)
        data, pl = load_params_lin(folder)
        if pl is None:
            report_lines.append(f"## {label}\n(missing params_lin in checkpoint/snapshot)\n")
            continue

        sys_params, S0, L0, G0, Eh = unpack(pl)
        report_lines.append("")
        report_lines.append("-" * 72)
        report_lines.append(f"Folder: {label}")
        report_lines.append("-" * 72)
        if isinstance(data, dict):
            for key in ("loss", "mse_hist_eh", "r2_eh", "r2_0", "mega"):
                if key in data:
                    report_lines.append(f"  {key}: {data[key]}")
        report_lines.append("")
        for name, val in zip(PARAM_NAMES, pl):
            report_lines.append(f"  {name:6s} = {val:.12e}")
        report_lines.append("")

        y0 = [S0, L0, G0]
        sol30 = solve_ivp(
            system,
            (0, 30),
            y0,
            t_eval=t_eval_30,
            args=(0.0, *sys_params),
            method="LSODA",
            atol=atol,
            rtol=rtol,
        )
        sol12 = solve_ivp(
            system,
            (0, 12),
            y0,
            t_eval=t_eval_12,
            args=(Eh, *sys_params),
            method="LSODA",
            atol=atol,
            rtol=rtol,
        )

        if not sol30.success or not sol12.success:
            report_lines.append("  (solve_ivp failed; no figures written)")
            continue

        t30, S30, L30 = sol30.t, sol30.y[0], sol30.y[1]
        t12, S12, L12 = sol12.t, sol12.y[0], sol12.y[1]
        years30 = 1954 + t30
        years12 = 1954 + t12

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(years30, S30, label="Sparrows (S)", color="tab:blue", linewidth=1.8)
        ax.plot(years30, L30, label="Locusts (L)", color="tab:orange", linewidth=1.8)
        ax.set_xlabel("Calendar year")
        ax.set_ylabel("Population index")
        ax.set_title(f"{label}: 30-year baseline (no hunting)")
        ax.legend()
        ax.grid(True, alpha=0.35)
        fig.tight_layout()
        p30 = os.path.join(folder, "populations_30yr_baseline.png")
        fig.savefig(p30, dpi=150)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(years12, S12, label="Sparrows (S)", color="tab:blue", linewidth=1.8)
        ax.plot(years12, L12, label="Locusts (L)", color="tab:orange", linewidth=1.8)
        ax.axvspan(1954 + 4.0, 1954 + 6.5, color="gray", alpha=0.2, label="Hunting on S")
        ax.set_xlabel("Calendar year")
        ax.set_ylabel("Population index")
        ax.set_title(f"{label}: 12-year historical (Eh = {Eh:.6g})")
        ax.legend()
        ax.grid(True, alpha=0.35)
        fig.tight_layout()
        p12 = os.path.join(folder, "populations_12yr_historical.png")
        fig.savefig(p12, dpi=150)
        plt.close(fig)

        report_lines.append(f"  Figures: populations_30yr_baseline.png, populations_12yr_historical.png")

    report_lines.append("")
    report_lines.append("=" * 72)
    out_txt = os.path.join(root, "REPORT.txt")
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(out_txt)


if __name__ == "__main__":
    main()
