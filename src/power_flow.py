"""Power flow execution and result extraction."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pandapower as pp

from src.metrics import Limits, compute_system_losses, count_overloads, count_voltage_violations


@dataclass
class PowerFlowResult:
    converged: bool
    message: str
    bus_results: pd.DataFrame
    line_results: pd.DataFrame
    trafo_results: pd.DataFrame
    warnings: list[str]
    system_losses_mw: float


def run_power_flow(net, limits: Limits | None = None) -> PowerFlowResult:
    """Run AC power flow and return a structured result object."""
    limits = limits or Limits()

    try:
        pp.runpp(net, init="auto", calculate_voltage_angles=True)
    except Exception as exc:  # noqa: BLE001 - user-facing robust error reporting
        return PowerFlowResult(
            converged=False,
            message=f"Power flow failed: {exc}",
            bus_results=pd.DataFrame(),
            line_results=pd.DataFrame(),
            trafo_results=pd.DataFrame(),
            warnings=["Non-convergence detected."],
            system_losses_mw=0.0,
        )

    warnings: list[str] = []

    volt_viol = count_voltage_violations(net, limits)
    line_ov, trafo_ov = count_overloads(net, limits)

    if volt_viol > 0:
        warnings.append(f"Voltage violations: {volt_viol} bus(es) outside {limits.v_min:.2f}-{limits.v_max:.2f} pu.")
    if line_ov > 0:
        warnings.append(f"Line overloads: {line_ov} line(s) above {limits.line_max_loading:.1f}%.")
    if trafo_ov > 0:
        warnings.append(f"Transformer overloads: {trafo_ov} transformer(s) above {limits.trafo_max_loading:.1f}%.")

    bus_results = net.res_bus.copy()
    line_results = net.res_line.copy()
    trafo_results = net.res_trafo.copy() if hasattr(net, "res_trafo") else pd.DataFrame()

    return PowerFlowResult(
        converged=True,
        message="Power flow converged successfully.",
        bus_results=bus_results,
        line_results=line_results,
        trafo_results=trafo_results,
        warnings=warnings,
        system_losses_mw=compute_system_losses(net),
    )
