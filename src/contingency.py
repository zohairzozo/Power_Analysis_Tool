"""N-1 and N-2 contingency analysis."""

from __future__ import annotations

from itertools import combinations
from typing import Iterable

import pandas as pd
import pandapower as pp

from src.metrics import Limits, count_voltage_violations, severity_score


def _evaluate_case(net, outaged: str, limits: Limits) -> dict:
    try:
        pp.runpp(net, init="auto", calculate_voltage_angles=True)
        converged = True
    except Exception:  # noqa: BLE001 - resilient contingency batch processing
        converged = False

    if not converged:
        return {
            "outaged_component": outaged,
            "converged": False,
            "max_line_loading_percent": float("nan"),
            "min_bus_voltage_pu": float("nan"),
            "max_bus_voltage_pu": float("nan"),
            "overloaded_lines": 0,
            "voltage_violations": 0,
            "severity_score": severity_score(False, 0.0, 1.0, 1.0, limits, 0, 0),
        }

    max_loading = float(net.res_line["loading_percent"].max()) if not net.res_line.empty else 0.0
    min_vm = float(net.res_bus["vm_pu"].min()) if not net.res_bus.empty else 1.0
    max_vm = float(net.res_bus["vm_pu"].max()) if not net.res_bus.empty else 1.0
    overloaded_lines = int((net.res_line["loading_percent"] > limits.line_max_loading).sum()) if not net.res_line.empty else 0
    voltage_violations = count_voltage_violations(net, limits)

    return {
        "outaged_component": outaged,
        "converged": True,
        "max_line_loading_percent": max_loading,
        "min_bus_voltage_pu": min_vm,
        "max_bus_voltage_pu": max_vm,
        "overloaded_lines": overloaded_lines,
        "voltage_violations": voltage_violations,
        "severity_score": severity_score(
            True,
            max_loading,
            min_vm,
            max_vm,
            limits,
            overloaded_lines,
            voltage_violations,
        ),
    }


def run_n1_contingency(net, include_trafos: bool = False, limits: Limits | None = None) -> pd.DataFrame:
    """Run N-1 line (and optional transformer) outages."""
    limits = limits or Limits()
    records: list[dict] = []

    for idx in net.line.index:
        original_status = bool(net.line.at[idx, "in_service"])
        net.line.at[idx, "in_service"] = False
        records.append(_evaluate_case(net, f"line_{idx}", limits))
        net.line.at[idx, "in_service"] = original_status

    if include_trafos and hasattr(net, "trafo") and not net.trafo.empty:
        for idx in net.trafo.index:
            original_status = bool(net.trafo.at[idx, "in_service"])
            net.trafo.at[idx, "in_service"] = False
            records.append(_evaluate_case(net, f"trafo_{idx}", limits))
            net.trafo.at[idx, "in_service"] = original_status

    df = pd.DataFrame(records)
    if df.empty:
        return df
    return df.sort_values("severity_score", ascending=False).reset_index(drop=True)


def generate_n2_pairs(line_indices: Iterable[int], max_cases: int | None = None) -> list[tuple[int, int]]:
    pairs = list(combinations(list(line_indices), 2))
    if max_cases is not None and max_cases > 0:
        return pairs[:max_cases]
    return pairs


def run_n2_contingency(
    net,
    max_cases: int = 200,
    limits: Limits | None = None,
    progress_callback=None,
) -> pd.DataFrame:
    """Run N-2 line outage pairs with optional progress callback."""
    limits = limits or Limits()
    pairs = generate_n2_pairs(net.line.index, max_cases=max_cases)

    records: list[dict] = []
    total = max(len(pairs), 1)

    for i, (line_a, line_b) in enumerate(pairs, start=1):
        original_a = bool(net.line.at[line_a, "in_service"])
        original_b = bool(net.line.at[line_b, "in_service"])
        net.line.at[line_a, "in_service"] = False
        net.line.at[line_b, "in_service"] = False
        records.append(_evaluate_case(net, f"line_{line_a}+line_{line_b}", limits))
        net.line.at[line_a, "in_service"] = original_a
        net.line.at[line_b, "in_service"] = original_b

        if progress_callback:
            progress_callback(i / total)

    df = pd.DataFrame(records)
    if df.empty:
        return df
    return df.sort_values("severity_score", ascending=False).reset_index(drop=True)
