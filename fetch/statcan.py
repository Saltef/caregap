import io, json, zipfile, logging, requests
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# -- Paths --
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR, OUT_DIR = ROOT / "data" / "raw", ROOT / "data" / "processed"
META_FILE = ROOT / "data" / "metadata.json"
for d in [RAW_DIR, OUT_DIR]: d.mkdir(parents=True, exist_ok=True)

TABLE_POP_HR = "17100142"
INPUT_PROCESSED = ROOT / "inputData" / "processed data"
LHIN_HR_MAP = {
    "Erie St. Clair": "3540", "South West": "3530", "Waterloo Wellington": "3520",
    "Hamilton Niagara Haldimand Brant": "3510", "Central West": "3560",
    "Mississauga Halton": "3550", "Toronto Central": "3595", "Central": "3570",
    "Central East": "3580", "South East": "3500", "Champlain": "3615",
    "North Simcoe Muskoka": "3575", "North East": "3590", "North West": "3610"
}
STATCAN_AGE_MAP = {
    "0 to 4 years": "0–14", "5 to 9 years": "0–14", "10 to 14 years": "0–14",
    "15 to 19 years": "15–24", "20 to 24 years": "15–24",
    "25 to 29 years": "25–44", "30 to 34 years": "25–44", "35 to 39 years": "25–44", "40 to 44 years": "25–44",
    "45 to 49 years": "45–64", "50 to 54 years": "45–64", "55 to 59 years": "45–64", "60 to 64 years": "45–64",
    "65 to 69 years": "65–74", "70 to 74 years": "65–74",
    "75 to 79 years": "75–84", "80 to 84 years": "75–84",
    "85 years and over": "85+"
}

FALLBACK_AGE_SHARES = {
    "0–14": 0.16,
    "15–24": 0.12,
    "25–44": 0.26,
    "45–64": 0.26,
    "65–74": 0.11,
    "75–84": 0.06,
    "85+": 0.03,
}


def _first_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _fallback_population_by_lhin(out_path: Path) -> pd.DataFrame:
    providers_path = INPUT_PROCESSED / "providers_by_lhin.csv"
    coords_path = ROOT / "data" / "static" / "lhin_coords.csv"

    if not providers_path.exists():
        raise FileNotFoundError(f"Fallback source missing: {providers_path}")

    providers = pd.read_csv(providers_path)
    if "lhin" not in providers.columns or "population" not in providers.columns:
        raise ValueError("Fallback providers file must include 'lhin' and 'population' columns")

    lhin_pop = (
        providers[["lhin", "population"]]
        .dropna()
        .drop_duplicates(subset=["lhin"])
        .rename(columns={"lhin": "LHIN"})
    )

    rows = []
    for _, row in lhin_pop.iterrows():
        for age_group, share in FALLBACK_AGE_SHARES.items():
            rows.append(
                {
                    "LHIN": row["LHIN"],
                    "year": 2024,
                    "age_group": age_group,
                    "population": int(round(float(row["population"]) * share)),
                }
            )

    out = pd.DataFrame(rows)
    if coords_path.exists():
        coords = pd.read_csv(coords_path)
        if {"lhin_name", "lat", "lon"}.issubset(coords.columns):
            out = out.merge(coords, left_on="LHIN", right_on="lhin_name", how="left")

    out.to_csv(out_path, index=False)
    log.warning("StatsCan schema mismatch detected; wrote fallback data to %s", out_path)
    return out

def _download_csv(table_id):
    api_url = f"https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/{table_id}/en"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(api_url, headers=headers).json()
    r = requests.get(resp['object'], headers=headers)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        csv_name = [n for n in z.namelist() if n.endswith(".csv") and "MetaData" not in n][0]
        return pd.read_csv(z.open(csv_name), low_memory=False)

def fetch_population_by_lhin():
    log.info("Starting LHIN Population Fetch...")
    df = _download_csv(TABLE_POP_HR)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Older table versions included explicit age columns; if absent, use local fallback.
    age_col = next((c for c in df.columns if "age" in c), None)
    if age_col is None:
        return _fallback_population_by_lhin(OUT_DIR / "population_by_age_lhin.csv")

    df["mapped_age"] = df[age_col].map(STATCAN_AGE_MAP)

    ref_date_col = _first_col(df, ["ref_date", "reference_period"])
    if ref_date_col is None:
        return _fallback_population_by_lhin(OUT_DIR / "population_by_age_lhin.csv")
    df["year"] = pd.to_numeric(df[ref_date_col].astype(str).str[:4], errors="coerce")

    inv_map = {v: k for k, v in LHIN_HR_MAP.items()}
    dguid_col = next((c for c in df.columns if "dguid" in c), None)
    if dguid_col is None:
        return _fallback_population_by_lhin(OUT_DIR / "population_by_age_lhin.csv")
    df["LHIN"] = df[dguid_col].astype(str).str[-4:].map(inv_map)

    # Filter for valid rows
    df = df[df["mapped_age"].notna() & df["LHIN"].notna()]
    val_col = _first_col(df, ["value", "val", "population"])
    if val_col is None:
        return _fallback_population_by_lhin(OUT_DIR / "population_by_age_lhin.csv")
    
    # Aggregate: Summing everything (including all sexes) into one LHIN/Age/Year bucket
    out = df.groupby(["LHIN", "year", "mapped_age"], as_index=False)[val_col].sum()
    out.columns = ["LHIN", "year", "age_group", "population"]

    out_path = OUT_DIR / "population_by_age_lhin.csv"
    out.to_csv(out_path, index=False)
    log.info(f"✅ SUCCESS: File saved to {out_path}")

if __name__ == "__main__":
    fetch_population_by_lhin()
