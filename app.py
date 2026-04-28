"""Streamlit app for interactive power system analysis."""

from __future__ import annotations

import streamlit as st
import plotly.express as px

from src.contingency import run_n1_contingency, run_n2_contingency
from src.metrics import Limits, summary_cards
from src.network_loader import list_available_systems, load_builtin_system, load_uploaded_network
from src.opf import run_opf
from src.power_flow import run_power_flow
from src.utils import EXPLANATIONS, build_contingency_report, critical_elements, dataframe_to_csv_bytes
from src.visualization import build_topology_figure

st.set_page_config(page_title="Power System Analysis Tool", page_icon="⚡", layout="wide")

st.title("⚡ Interactive Power System Analysis Tool")
st.caption("Pandapower-based dashboard for load flow, contingency analysis, and OPF.")

LIMITS = Limits(v_min=0.95, v_max=1.05, line_max_loading=100.0, trafo_max_loading=100.0)


@st.cache_resource
def get_network(case_name: str):
    return load_builtin_system(case_name)


def render_summary(net):
    cards = summary_cards(net, LIMITS)
    cols = st.columns(6)
    cols[0].metric("Total Generation (MW)", f"{cards['total_generation_mw']:.2f}")
    cols[1].metric("Total Load (MW)", f"{cards['total_load_mw']:.2f}")
    cols[2].metric("System Losses (MW)", f"{cards['system_losses_mw']:.2f}")
    cols[3].metric("Max Line Loading (%)", f"{cards['max_line_loading_percent']:.2f}")
    cols[4].metric("Minimum Voltage (pu)", f"{cards['minimum_voltage_pu']:.4f}")
    cols[5].metric("# Violations", f"{cards['violations']}")


with st.sidebar:
    st.header("Configuration")
    selected_case = st.selectbox("Select built-in test system", list_available_systems(), index=0)

    upload = st.file_uploader(
        "Or upload custom network (.json/.p/.pickle)",
        type=["json", "p", "pickle"],
        accept_multiple_files=False,
    )

    st.markdown("---")
    include_trafos = st.checkbox("Include transformers in N-1", value=False)
    n2_limit = st.number_input("N-2 max outage pairs", min_value=10, max_value=5000, value=200, step=10)

    st.markdown("---")
    run_pf = st.button("Run Power Flow", use_container_width=True)
    run_n1 = st.button("Run N-1 Contingency", use_container_width=True)
    run_n2 = st.button("Run N-2 Contingency", use_container_width=True)
    run_opf_btn = st.button("Run OPF", use_container_width=True)

try:
    if upload:
        net = load_uploaded_network(upload.name, upload.getvalue())
        st.sidebar.success("Loaded custom network")
    else:
        net = get_network(selected_case)
except Exception as exc:  # noqa: BLE001
    st.error(f"Failed to load network: {exc}")
    st.stop()

if "n1_results" not in st.session_state:
    st.session_state.n1_results = None
if "n2_results" not in st.session_state:
    st.session_state.n2_results = None
if "opf_results" not in st.session_state:
    st.session_state.opf_results = None

# auto-run baseline PF for visualization context
pf_result = run_power_flow(net, LIMITS)

if run_pf:
    pf_result = run_power_flow(net, LIMITS)

if not pf_result.converged:
    st.error(pf_result.message)
else:
    st.success(pf_result.message)
    for warning in pf_result.warnings:
        st.warning(warning)

render_summary(net)

col_left, col_right = st.columns([1.65, 1.0])
with col_left:
    st.plotly_chart(build_topology_figure(net), use_container_width=True)

with col_right:
    st.subheader("Concepts")
    for key, val in EXPLANATIONS.items():
        with st.expander(key, expanded=False):
            st.write(val)

    st.subheader("Critical Elements")
    crit = critical_elements(net)
    if not crit["critical_lines"].empty:
        st.write("Most loaded lines")
        st.dataframe(crit["critical_lines"], use_container_width=True)
    if not crit["critical_buses"].empty:
        st.write("Largest voltage deviations")
        st.dataframe(crit["critical_buses"], use_container_width=True)

st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs(["Power Flow Results", "N-1", "N-2", "OPF"])

with tab1:
    st.subheader("Bus Results")
    st.dataframe(pf_result.bus_results, use_container_width=True)
    st.subheader("Line Results")
    st.dataframe(pf_result.line_results, use_container_width=True)
    if not pf_result.trafo_results.empty:
        st.subheader("Transformer Results")
        st.dataframe(pf_result.trafo_results, use_container_width=True)

    st.download_button(
        "Download power flow bus results CSV",
        data=dataframe_to_csv_bytes(pf_result.bus_results),
        file_name="power_flow_bus_results.csv",
        mime="text/csv",
    )

with tab2:
    if run_n1:
        with st.spinner("Running N-1 contingency analysis..."):
            st.session_state.n1_results = run_n1_contingency(net, include_trafos=include_trafos, limits=LIMITS)

    if st.session_state.n1_results is not None and not st.session_state.n1_results.empty:
        n1_df = st.session_state.n1_results
        st.dataframe(n1_df, use_container_width=True)
        top10 = n1_df.head(10)
        fig = px.bar(top10, x="outaged_component", y="severity_score", title="Top 10 Most Severe N-1 Contingencies")
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    if run_n2:
        progress = st.progress(0.0)

        def _cb(val: float) -> None:
            progress.progress(val)

        with st.spinner("Running N-2 contingency analysis..."):
            st.session_state.n2_results = run_n2_contingency(net, max_cases=int(n2_limit), limits=LIMITS, progress_callback=_cb)

    if st.session_state.n2_results is not None and not st.session_state.n2_results.empty:
        n2_df = st.session_state.n2_results
        st.dataframe(n2_df, use_container_width=True)
        st.plotly_chart(
            px.bar(n2_df.head(10), x="outaged_component", y="severity_score", title="Top 10 Most Severe N-2 Cases"),
            use_container_width=True,
        )

with tab4:
    if run_opf_btn:
        with st.spinner("Running OPF..."):
            st.session_state.opf_results = run_opf(net)

    if st.session_state.opf_results is not None:
        opf_res = st.session_state.opf_results
        if not opf_res["converged"]:
            st.error(opf_res["message"])
            st.info("Possible causes: infeasible limits, missing generator flexibility, or disconnected topology.")
        else:
            st.success(opf_res["message"])
            st.metric("Total generation cost (EUR)", f"{opf_res['total_cost']:.2f}")
            st.write("Generator dispatch")
            st.dataframe(opf_res["gen_dispatch"], use_container_width=True)
            st.write("OPF bus voltages")
            st.dataframe(opf_res["net"].res_bus, use_container_width=True)
            st.write("OPF line loading")
            st.dataframe(opf_res["net"].res_line, use_container_width=True)

if st.session_state.n1_results is not None:
    report_bytes = build_contingency_report(st.session_state.n1_results, st.session_state.n2_results)
    st.download_button(
        "Download contingency report",
        data=report_bytes,
        file_name="contingency_report.csv",
        mime="text/csv",
    )
