"""Optimal power flow utilities."""

from __future__ import annotations

import pandas as pd
import pandapower as pp


def _ensure_costs(net) -> None:
    """Create simple linear cost functions for generators/ext_grid if missing."""
    if net.poly_cost.empty:
        for gen_idx in net.gen.index:
            pp.create_poly_cost(net, gen_idx, "gen", cp1_eur_per_mw=20.0, cp0_eur=0.0)
        for eg_idx in net.ext_grid.index:
            pp.create_poly_cost(net, eg_idx, "ext_grid", cp1_eur_per_mw=40.0, cp0_eur=0.0)


def run_opf(net) -> dict:
    """Run OPF minimizing generation cost."""
    opf_net = net

    # Make sure controllable elements have reasonable limits.
    if not opf_net.gen.empty:
        opf_net.gen["min_p_mw"] = opf_net.gen.get("min_p_mw", 0.0).fillna(0.0)
        opf_net.gen["max_p_mw"] = opf_net.gen.get("max_p_mw", opf_net.gen["p_mw"] * 1.5 + 1.0).fillna(opf_net.gen["p_mw"] * 1.5 + 1.0)
        opf_net.gen["controllable"] = True

    if not opf_net.ext_grid.empty:
        opf_net.ext_grid["min_p_mw"] = opf_net.ext_grid.get("min_p_mw", -1e9).fillna(-1e9)
        opf_net.ext_grid["max_p_mw"] = opf_net.ext_grid.get("max_p_mw", 1e9).fillna(1e9)

    _ensure_costs(opf_net)

    try:
        pp.runopp(opf_net, calculate_voltage_angles=True, init="flat")
    except Exception as exc:  # noqa: BLE001 - user-friendly OPF error reporting
        return {
            "converged": False,
            "message": f"OPF failed to converge: {exc}",
            "net": opf_net,
            "gen_dispatch": pd.DataFrame(),
            "total_cost": float("nan"),
        }

    total_cost = float(opf_net.res_cost) if hasattr(opf_net, "res_cost") else float("nan")

    gen_dispatch = opf_net.res_gen[["p_mw", "q_mvar"]].copy() if not opf_net.res_gen.empty else pd.DataFrame()

    return {
        "converged": True,
        "message": "OPF converged successfully.",
        "net": opf_net,
        "gen_dispatch": gen_dispatch,
        "total_cost": total_cost,
    }
