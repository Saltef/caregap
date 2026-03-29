"""
fetch/statcan.py
────────────────
Updated 2026 version. 
Fixes: Explicit path resolution for cloud environments (Codespaces).
"""
import io
import json
import zipfile
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
import requests

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# ── Bulletproof Path Resolution ─────────────────────────────────────────────
# This ensures that no matter where you run the script from, 
# it finds the project root 'ontario-health-intel'
CURRENT_FILE = Path(__file__).resolve()
ROOT = CURRENT_FILE.parent.parent

# Create data directories explicitly
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"
META_FILE = ROOT / "data" / "metadata.json"

for folder in [RAW_DIR, OUT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

print(f"🚀 Data Pipeline Initialized")
print(f"📍 Root Directory: {ROOT}")
print(f"📁 Saving Processed Data to: {OUT_DIR.resolve()}")

# ── Rest of your logic remains the same (Endpoints & Maps) ──────────────────
TABLE_POP_HR    = "17100142"
TABLE_PROJ      = "17100057"

LHIN_HR_MAP = {
    "Erie St. Clair": "3540", "South West": "3530", "Waterloo Wellington": "3520",
    "Hamilton Niagara Haldimand Brant": "3510", "Central West": "3560",
    "Mississauga Halton": "3550", "Toronto Central": "3595", "Central": "3570",
    "Central East": "3580", "South East": "3500", "Champlain": "3615",
    "North Simcoe Muskoka": "3575", "North East": "3590", "North West": "3610",
}

STATCAN_AGE_MAP = {
    "0 to 4 years": "0–14", "5 to 9 years": "0–14", "10 to 14 years": "0–14",
    "15 to 19 years": "15–24", "20 to 24 years": "15–24",
    "25 to 29 years": "25–44", "30 to 34 years": "25–44", "35 to 39 years": "25–44", "40 to 44 years": "25–44",
    "45 to 49 years": "45–64", "50 to 54 years": "45–64", "55 to 59 years": "45–64", "60 to 64 years": "45–64",
    "65 to 69 years": "65–74", "70 to 74 years": "65–74",
    "75 to 79 years": "75–84", "80 to 84 years": "75–84",
    "85 years and over": "85+",
}

def _download_csv(table_id: str) -> pd.DataFrame:
    api_url = f"https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/{table_id}/en"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(api_url, headers=headers, timeout=30)
        resp.raise_for_status()
        download_url = resp.json().get("object")
        r = requests.get(download_url, headers=headers, timeout=120)
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            csv_name = [n for n in z.namelist() if n.endswith(".csv") and "MetaData" not in n][0]
            data = z.read(csv_name)
            (RAW_DIR / f"statcan_{table_id}.csv").write_bytes(data)
            return pd.read_csv(io.BytesIO(data), encoding="utf-8-sig", low_memory=False)
    except Exception as e:
        log.error(f"Failure fetching {table_id}: {e}")
        raise

def fetch_population_by_lhin():
    df = _download_csv(TABLE_POP_HR)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df[df["geo"].str.contains("Ontario", na=False)].copy()
    
    # Map LHINs
    inv_map = {v: k for k, v in LHIN_HR_MAP.items()}
    dguid_col = next((c for c in df.columns if "dguid" in c), "dguid")
    df["hr_code"] = df[dguid_col].astype(str).str[-4:]
    df["LHIN"] = df["hr_code"].map(inv_map)
    
    # Map Age
    age_col = next((c for c in df.columns if "age" in c), "age_group")
    df["age_group_mapped"] = df[age_col].map(STATCAN_AGE_MAP)
    df = df[df["age_group_mapped"].notna() & df["LHIN"].notna()]
    
    # Aggregate
    df["year"] = pd.to_numeric(df["ref_date"].astype(str).str[:4], errors="coerce")
    out = df.groupby(["LHIN", "year", "age_group_mapped"], as_index=False)["value"].sum()
    out.columns = ["LHIN", "year", "age_group", "population"]
    
    out.to_csv(OUT_DIR / "population_by_age_lhin.csv", index=False)
    log.info(f"✅ Saved LHIN Data to {OUT_DIR}")
    return out

if __name__ == "__main__":
    fetch_population_by_lhin()
