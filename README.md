# Thales Predictive Maintenance Dashboard

A Streamlit decision-support application for detecting subtle deviations in manufacturing telemetry before failures occur. It shifts operations from reactive to predictive maintenance using machine-specific baselines and Isolation Forest anomaly detection.

## What the app provides

- Maintenance overview with risk distribution and high-risk asset count
- Per-machine anomaly and sensor-deviation trends
- A prioritized maintenance alert panel with CSV export
- Historical risk escalation analysis and maintenance-mode comparison
- Controls for machine, risk threshold, time window, and operation mode

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

The application expects `Thales_Group_Manufacturing.csv` next to `app.py`.

## Methodology

The workflow establishes rolling median sensor baselines per machine, engineers normalized deviations and error trends, and scores rare multivariate patterns with an Isolation Forest. Scores are normalized to 0-100 and classified as Low, Medium, or High risk. See `deliverables/` for the research paper and executive summary.

## Repository layout

```text
app.py                         Streamlit dashboard
Thales_Group_Manufacturing.csv Uploaded telemetry dataset
deliverables/                  Research paper and stakeholder summary
requirements.txt               Runtime dependencies
```
