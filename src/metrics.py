"""Metrics and post-processing utilities."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Limits:
    v_min: float = 0.95
    v_max: float = 1.05
    line_max_loading: float = 100.0
    trafo_max_loading: float = 100.0


def compute_system_losses(net) -> float:
    """Compute active power losses in MW."""
    line_losses = 0.0
    trafo_losses = 0.0

    if not net.res_line.empty:
        line_losses = float((net.res_line["pl_mw"].fillna(0.0)).sum())

    if hasattr(net, "res_trafo") and not net.res_trafo.empty:
        # Positive values generally represent losses in pandapower result conventions.
        trafo_losses = float(net.res_trafo.get("pl_mw", pd.Series(dtype=float)).fillna(0.0).sum())

    return max(line_losses + trafo_losses, 0.0)


def count_voltage_violations(net, limits: Limits) -> int:
    if net.res_bus.empty:
        return 0
    vm = net.res_bus["vm_pu"].fillna(1.0)
    return int(((vm < limits.v_min) | (vm > limits.v_max)).sum())


def count_overloads(net, limits: Limits) -> tuple[int, int]:
    line_ov = 0
    trafo_ov = 0
    if not net.res_line.empty and "loading_percent" in net.res_line:
        line_ov = int((net.res_line["loading_percent"].fillna(0.0) > limits.line_max_loading).sum())
    if hasattr(net, "res_trafo") and not net.res_trafo.empty and "loading_percent" in net.res_trafo:
        trafo_ov = int((net.res_trafo["loading_percent"].fillna(0.0) > limits.trafo_max_loading).sum())
    return line_ov, trafo_ov


def severity_score(
    converged: bool,
    max_loading: float,
    min_vm: float,
    max_vm: float,
    limits: Limits,
    line_overloads: int,
    voltage_violations: int,
) -> float:
    """Weighted severity score for contingency ranking."""
    if not converged:
        return 1_000.0

    overload_severity = max(0.0, max_loading - limits.line_max_loading)
    under_voltage = max(0.0, limits.v_min - min_vm)
    over_voltage = max(0.0, max_vm - limits.v_max)
    voltage_severity = (under_voltage + over_voltage) * 100.0

    return (
        2.5 * overload_severity
        + 5.0 * voltage_severity
        + 20.0 * line_overloads
        + 15.0 * voltage_violations
    )


def summary_cards(net, limits: Limits) -> dict[str, float | int]:
    total_gen = float(net.res_gen["p_mw"].sum()) if not net.res_gen.empty else 0.0
    ext_grid_gen = float(net.res_ext_grid["p_mw"].sum()) if not net.res_ext_grid.empty else 0.0
    total_load = float(net.load["p_mw"].sum()) if not net.load.empty else 0.0
    losses = compute_system_losses(net)
    max_loading = float(net.res_line["loading_percent"].max()) if not net.res_line.empty else 0.0
    min_vm = float(net.res_bus["vm_pu"].min()) if not net.res_bus.empty else np.nan

    line_ov, trafo_ov = count_overloads(net, limits)
    volt_viol = count_voltage_violations(net, limits)

    return {
        "total_generation_mw": total_gen + ext_grid_gen,
        "total_load_mw": total_load,
        "system_losses_mw": losses,
        "max_line_loading_percent": max_loading,
        "minimum_voltage_pu": min_vm,
        "violations": int(line_ov + trafo_ov + volt_viol),
    }
