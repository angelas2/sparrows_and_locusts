#!/usr/bin/env python3
"""
Load good #1 checkpoint params_lin, set ONLY sparrow death a3 (index 9) and
locust death b4 (index 11) to 1/3 and 1.0 — all other numbers unchanged.

Note: famine_model.system() uses module FIXED_A3 / FIXED_B4 for dynamics, not
the tuple slots; for these graphs we temporarily set those constants to match
the array so the figures reflect the stated death rates.

Writes PNGs under ./plots_only_a3_b4_changed/ next to this script.
"""
from __future__ import annotations

import json
import os
import shutil
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

import famine_model as fm

HERE = os.path.dirname(os.path.abspath(__file__))
CK = os.path.join(HERE, "checkpoint.json")
OUT = os.path.join(HERE, "plots_only_a3_b4_changed")
A3 = 1.0 / 3.0
B4 = 1.0


def main() -> int:
    with open(CK, encoding="utf-8") as f:
        ck = json.load(f)
    pl = [float(x) for x in ck["params_lin"]]
    if len(pl) != 16:
        print(f"Expected 16 params_lin, got {len(pl)}", file=sys.stderr)
        return 1

    old_a3, old_b4 = pl[9], pl[11]
    pl[9] = A3
    pl[11] = B4

    os.makedirs(OUT, exist_ok=True)
    meta = {
        "source_checkpoint": CK,
        "params_lin_original_a3_b4": [old_a3, old_b4],
        "params_lin_set_to": {"a3_index_9": A3, "b4_index_11": B4},
        "params_lin_full": pl,
    }
    with open(os.path.join(OUT, "params_used.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    saved_a3, saved_b4 = fm.FIXED_A3, fm.FIXED_B4
    try:
        fm.FIXED_A3 = A3
        fm.FIXED_B4 = B4
        fm.plot_results(
            pl,
            plot_name="good1_only_death_rates",
            save_plot_n=True,
            output_root=OUT,
        )
        g_std, r2_e, r2_z = fm.metrics_for_report(pl)
    finally:
        fm.FIXED_A3 = saved_a3
        fm.FIXED_B4 = saved_b4

    # Optional: copy plot_N to a descriptive name
    pN = os.path.join(OUT, "plot_N.png")
    if os.path.isfile(pN):
        shutil.copy2(pN, os.path.join(OUT, "good1_only_death_rates_plot_N.png"))
    print(f"Plots -> {OUT}/")
    print(f"  a3 {old_a3:.6g} -> {A3}; b4 {old_b4:.6g} -> {B4}")
    print(f"  g_std={g_std:.5f} R2_eh={r2_e:.4f} R2_0={r2_z:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
