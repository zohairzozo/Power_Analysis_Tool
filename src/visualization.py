"""Interactive topology visualization using Plotly."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go


def _bus_coords(net):
    if hasattr(net, "bus_geodata") and not net.bus_geodata.empty:
        x = net.bus_geodata["x"].reindex(net.bus.index).fillna(0.0).to_numpy()
        y = net.bus_geodata["y"].reindex(net.bus.index).fillna(0.0).to_numpy()
    else:
        # fallback deterministic circular layout
        n = len(net.bus.index)
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
        x = np.cos(angles)
        y = np.sin(angles)
    return x, y


def build_topology_figure(net):
    """Build a topology graph figure with result-based styling."""
    x, y = _bus_coords(net)
    bus_pos = {bus_idx: (x[i], y[i]) for i, bus_idx in enumerate(net.bus.index)}

    fig = go.Figure()

    # draw lines with per-element loading style
    for idx, row in net.line.iterrows():
        if not row.get("in_service", True):
            continue

        fb, tb = row["from_bus"], row["to_bus"]
        x0, y0 = bus_pos[fb]
        x1, y1 = bus_pos[tb]

        loading = 0.0
        pf_mw = qf = 0.0
        if hasattr(net, "res_line") and idx in net.res_line.index:
            loading = float(net.res_line.at[idx, "loading_percent"])
            pf_mw = float(net.res_line.at[idx, "p_from_mw"])
            qf = float(net.res_line.at[idx, "q_from_mvar"])

        color = "#2ca02c" if loading <= 70 else "#ff7f0e" if loading <= 100 else "#d62728"
        width = 1.5 if loading <= 70 else 2.5 if loading <= 100 else 4

        fig.add_trace(
            go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines",
                line={"color": color, "width": width},
                hovertemplate=(
                    f"Line {idx}<br>Loading: {loading:.2f}%<br>"
                    f"P_from: {pf_mw:.2f} MW<br>Q_from: {qf:.2f} MVAr<extra></extra>"
                ),
                showlegend=False,
            )
        )

    # buses
    vm = net.res_bus["vm_pu"] if hasattr(net, "res_bus") and not net.res_bus.empty else None
    va = net.res_bus["va_degree"] if hasattr(net, "res_bus") and not net.res_bus.empty else None

    bus_hover = []
    colors = []
    symbols = []
    for bus_idx in net.bus.index:
        name = str(net.bus.at[bus_idx, "name"]) if "name" in net.bus.columns else f"Bus {bus_idx}"
        vm_i = float(vm.at[bus_idx]) if vm is not None and bus_idx in vm.index else float("nan")
        va_i = float(va.at[bus_idx]) if va is not None and bus_idx in va.index else float("nan")

        is_slack = (not net.ext_grid.empty) and (bus_idx in set(net.ext_grid["bus"].values))
        has_gen = (not net.gen.empty) and (bus_idx in set(net.gen["bus"].values))
        has_load = (not net.load.empty) and (bus_idx in set(net.load["bus"].values))

        if is_slack:
            colors.append("#1f77b4")
            symbols.append("diamond")
        elif has_gen:
            colors.append("#9467bd")
            symbols.append("square")
        elif has_load:
            colors.append("#17becf")
            symbols.append("circle")
        else:
            colors.append("#7f7f7f")
            symbols.append("circle-open")

        bus_hover.append(
            f"{name}<br>Bus: {bus_idx}<br>V: {vm_i:.4f} pu<br>Angle: {va_i:.2f}°"
        )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="markers+text",
            text=[str(i) for i in net.bus.index],
            textposition="top center",
            marker={"size": 13, "color": colors, "symbol": symbols, "line": {"width": 1, "color": "#222"}},
            hovertext=bus_hover,
            hoverinfo="text",
            name="Buses",
        )
    )

    fig.update_layout(
        template="plotly_white",
        title="Network Topology",
        xaxis={"visible": False},
        yaxis={"visible": False, "scaleanchor": "x", "scaleratio": 1},
        legend={"orientation": "h", "y": 1.02, "x": 0.01},
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        height=620,
    )

    return fig
