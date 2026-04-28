# Interactive Power System Analysis Tool

A ready-to-run Streamlit dashboard for practical transmission network analysis using **pandapower**.

## What this tool does

This application helps students and engineers:
- Load standard IEEE networks (9-bus, 14-bus, 30-bus) or upload custom pandapower networks.
- Visualize network topology interactively.
- Run AC power flow.
- Run N-1 and N-2 contingency analysis.
- Run OPF (Optimal Power Flow) with simple generator cost curves.
- Export results and contingency reports.

## Features

- **Interactive dashboard** with one-click analysis actions.
- **Topology visualization** with bus/line hover information and loading-based line styling.
- **Power flow analysis** with violation detection:
  - Voltage limits (0.95–1.05 pu)
  - Line overload limit (100%)
  - Transformer overload limit (100%)
- **N-1 contingency analysis** including severity ranking.
- **N-2 contingency analysis** with case limit and progress bar.
- **OPF** dispatch + total operating cost.
- **Summary cards** for generation, load, losses, voltage, loading, and violations.
- **CSV export** for key outputs.
- **Learning panels** with short explanations of PF, N-1, N-2, and OPF.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # on Windows use: .venv\Scripts\activate
pip install -r requirements.txt
```

## How to run

```bash
streamlit run app.py
```

## Basic checks

Run lightweight project checks:

```bash
python -m compileall app.py src
python scripts_smoke_check.py
```

## Example usage

1. Start the app and select **IEEE 14 Bus**.
2. Click **Run Power Flow** and inspect voltage profile and loading.
3. Click **Run N-1 Contingency** and review top severe outages.
4. Set N-2 limit (for example 100), run N-2, and inspect ranking.
5. Run **OPF** to view optimal dispatch and total cost.
6. Export contingency report and power flow CSV.

## Limitations

- N-2 analysis is combinatorial and can be computationally expensive for large networks.
- OPF feasibility depends on reasonable generator/ext-grid limits and cost definitions.
- Dynamic stability, short-circuit, and uncertainty scenarios are out of scope for this MVP.

## Future improvements

- Optional PyPSA backend integration for extended optimization workflows.
- Dynamic stability module (time-domain simulation workflow).
- Short-circuit and protection screening module.
- Renewable uncertainty/scenario analysis.
- Geographic layout support via map overlays.
- Background job execution for large contingency batches.

## Project structure

```text
.
├── app.py
├── requirements.txt
├── README.md
├── src/
│   ├── network_loader.py
│   ├── power_flow.py
│   ├── contingency.py
│   ├── opf.py
│   ├── visualization.py
│   ├── metrics.py
│   └── utils.py
├── data/
│   └── sample_networks/
└── outputs/
    └── reports/
```
