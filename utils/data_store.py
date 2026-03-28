import json
from datetime import datetime
from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
META_FILE = DATA_DIR / "metadata.json"


def _update_metadata(key, rows, source_file):
    meta = {}
    if META_FILE.exists():
        try:
            meta = json.loads(META_FILE.read_text(encoding="utf-8"))
        except Exception:
            meta = {}

    meta[key] = {
        "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": rows,
        "source_file": source_file,
        "source": "CIHI quick stats manual upload",
    }
    META_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _find_column(columns, candidates):
    lowered = {str(c).strip().lower(): c for c in columns}
    for candidate in candidates:
        col = lowered.get(candidate.lower())
        if col is not None:
            return col
    for col in columns:
        col_lower = str(col).strip().lower()
        if any(candidate.lower() in col_lower for candidate in candidates):
            return col
    return None


def process_cihi_upload(uploaded_file):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    try:
        save_path = RAW_DIR / uploaded_file.name
        save_path.write_bytes(uploaded_file.getbuffer())

        suffix = save_path.suffix.lower()
        if suffix in [".xlsx", ".xls"]:
            df = pd.read_excel(save_path)
        else:
            df = pd.read_csv(save_path)

        if df.empty:
            return False

        lhin_col = _find_column(df.columns, ["lhin", "health region", "region", "sub-region"])
        year_col = _find_column(df.columns, ["year", "ref_date", "fiscal year"])
        hosp_col = _find_column(df.columns, ["hospitalizations", "discharges", "admissions", "acsc"])
        er_col = _find_column(df.columns, ["er visits", "ed visits", "emergency visits"])

        if lhin_col is None or hosp_col is None:
            return False

        out = pd.DataFrame()
        out["LHIN"] = df[lhin_col].astype(str).str.strip()
        out["hospitalizations"] = pd.to_numeric(
            df[hosp_col].astype(str).str.replace(",", ""),
            errors="coerce",
        )

        if year_col is not None:
            out["year"] = pd.to_numeric(
                df[year_col].astype(str).str[:4],
                errors="coerce",
            ).fillna(datetime.utcnow().year)
        else:
            out["year"] = datetime.utcnow().year
        out["year"] = out["year"].astype(int)

        if er_col is not None:
            out["er_visits"] = pd.to_numeric(
                df[er_col].astype(str).str.replace(",", ""),
                errors="coerce",
            )

        out = out[(out["LHIN"] != "") & out["hospitalizations"].notna()].copy()
        if out.empty:
            return False

        out_path = PROCESSED_DIR / "hospitalizations_by_lhin.csv"
        out.to_csv(out_path, index=False)
        _update_metadata("hospitalizations_by_lhin", len(out), save_path.name)
        return True
    except Exception:
        return False


def get_projected_data(year, scenario, age_group):
    # 1. Load current LHIN populations
    df_lhin = pd.read_csv(DATA_DIR / "processed/population_by_age_lhin.csv")

    # 2. Load Provincial Projections
    df_proj = pd.read_csv(DATA_DIR / "processed/population_projections.csv")

    # 3. Load Coordinates
    coords = pd.read_csv(DATA_DIR / "static/lhin_coords.csv")

    # Calculate Growth Multiplier from Projections
    # (Provincial Pop in Target Year / Provincial Pop in Current Year)
    current_year = 2024  # Or latest in your data
    base_pop = df_proj[(df_proj["year"] == current_year) & (df_proj["age_group"] == age_group)]["population"].sum()
    target_pop = df_proj[
        (df_proj["year"] == year)
        & (df_proj["scenario_label"] == scenario)
        & (df_proj["age_group"] == age_group)
    ]["population"].sum()

    multiplier = target_pop / base_pop if base_pop > 0 else 1.0

    # Apply multiplier to current LHIN data
    df_lhin["projected_pop"] = df_lhin["population"] * multiplier

    # Merge with coordinates for the map
    df_final = df_lhin.merge(coords, left_on="LHIN", right_on="lhin_name")
    return df_final[df_final["age_group"] == age_group]
