"""General utility helpers for UI and reporting."""

from __future__ import annotations

from io import StringIO

import pandas as pd


EXPLANATIONS = {
    "Power Flow": "AC power flow computes steady-state bus voltages, angles, and line flows for current generation/load conditions.",
    "N-1": "N-1 contingency checks system security when any single component (for example one line) is out of service.",
    "N-2": "N-2 contingency checks robustness against simultaneous outage of two components and is computationally much heavier.",
    "OPF": "Optimal Power Flow finds an economically optimal dispatch while satisfying network constraints and operational limits.",
}


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def build_contingency_report(n1_df: pd.DataFrame, n2_df: pd.DataFrame | None = None) -> bytes:
    """Create a single CSV-like text report with multiple sections."""
    buffer = StringIO()
    buffer.write("# N-1 Contingency Results\n")
    n1_df.to_csv(buffer, index=False)

    if n2_df is not None and not n2_df.empty:
        buffer.write("\n# N-2 Contingency Results\n")
        n2_df.to_csv(buffer, index=False)

    return buffer.getvalue().encode("utf-8")


def critical_elements(net, top_n: int = 5) -> dict[str, pd.DataFrame]:
    """Return top critical lines and buses based on loading/voltage deviations."""
    lines = pd.DataFrame()
    buses = pd.DataFrame()

    if hasattr(net, "res_line") and not net.res_line.empty:
        lines = net.res_line[["loading_percent", "p_from_mw", "q_from_mvar"]].copy()
        lines = lines.sort_values("loading_percent", ascending=False).head(top_n)

    if hasattr(net, "res_bus") and not net.res_bus.empty:
        buses = net.res_bus[["vm_pu", "va_degree"]].copy()
        buses["vm_deviation"] = (buses["vm_pu"] - 1.0).abs()
        buses = buses.sort_values("vm_deviation", ascending=False).head(top_n)

    return {"critical_lines": lines, "critical_buses": buses}
