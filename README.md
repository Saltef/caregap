# Ontario Health Intel

Ontario Health Intel is a Python/Streamlit prototype for exploring Ontario population growth and primary-care pressure trends, with data ingestion paths for Statistics Canada and CIHI datasets.

## What Is In This Repo Right Now

The codebase currently has:

- Data fetch/load utilities for:
  - Statistics Canada (automated downloads)
  - CIHI (manual file download + normalization)
- Several dashboard prototypes (not all are fully production-ready yet)
- Basic data directories and metadata tracking

## Tech Stack

- Python
- Streamlit
- Pandas / NumPy
- Plotly / PyDeck / Leafmap
- GeoPandas

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Data Workflow

### 1) Fetch Statistics Canada datasets

This writes processed CSV outputs under `data/processed/` and updates `data/metadata.json`.

```powershell
python -m fetch.statcan
```

Outputs:

- `data/processed/population_by_age_lhin.csv`
- `data/processed/population_projections.csv`

### 2) Load CIHI datasets (manual source files)

Place CIHI files in `data/raw/` (for example `physicians_in_canada*.xlsx`, `regulated_nurses*.xlsx`), then run:

```powershell
python -m fetch.cihi_loader
```

Typical outputs:

- `data/processed/providers_by_lhin.csv`
- `data/processed/np_by_lhin.csv`

## Running Dashboards

This repo has multiple Streamlit entry points:

```powershell
streamlit run ontario_health_l1.py
streamlit run map_dashboard.py
streamlit run app\physician_map.py
streamlit run app\main.py
```

Notes:

- `ontario_health_l1.py` is the most self-contained demo (uses built-in baseline data).
- `map_dashboard.py` and `app/*` require processed files/geography assets to exist first.

## Repository Layout

```text
app/                 Streamlit app modules
fetch/               Data ingestion and normalization scripts
pages/               Streamlit multipage files
scripts/             Older/auxiliary data sync scripts
utils/               Shared data helpers
data/
  raw/               Source files (downloaded/uploaded)
  processed/         Cleaned outputs for dashboards
  static/            Static lookup files (for example LHIN coordinates)
  metadata.json      Dataset freshness + provenance
```

## Current Implementation Gaps (Observed From Code)

- `pages/00_data_manager.py` currently fails compilation (`IndentationError` at line 4).
- `pages/00_data_manager.py` references `process_cihi_upload` in `utils.data_store`, but that function is not present.
- `app/main.py` references `gpd` without importing `geopandas as gpd`.
- Some dashboards expect geography files under `data/geography/` that are not committed in this repo snapshot.

## Suggested Order For Local Use

1. Install dependencies.
2. Run `python -m fetch.statcan`.
3. (Optional) add CIHI files and run `python -m fetch.cihi_loader`.
4. Start with `streamlit run ontario_health_l1.py`.
