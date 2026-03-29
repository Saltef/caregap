import io, json, zipfile, logging, requests
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TABLE_ID = "17100142"

# Ontario Health Region (LHIN) Mapping
LHIN_MAP = {
    "3540": "Erie St. Clair", "3530": "South West", "3520": "Waterloo Wellington",
    "3510": "HNHB", "3560": "Central West", "3550": "Mississauga Halton",
    "3595": "Toronto Central", "3570": "Central", "3580": "Central East",
    "3500": "South East", "3615": "Champlain", "3575": "North Simcoe Muskoka",
    "3590": "North East", "3610": "North West"
}

STATCAN_AGE_MAP = {
    "0 to 4 years": "0–14", "5 to 9 years": "0–14", "10 to 14 years": "0–14",
    "15 to 19 years": "15–24", "20 to 24 years": "15–24",
    "65 to 69 years": "65–74", "70 to 74 years": "65–74",
    "75 to 79 years": "75–84", "80 to 84 years": "75–84",
    "85 years and over": "85+"
}

def fetch_population_by_lhin():
    log.info(f"Fetching Table {TABLE_ID} from StatCan...")
    api_url = f"https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/{TABLE_ID}/en"
    
    try:
        download_url = requests.get(api_url).json()['object']
        r = requests.get(download_url)
        
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            csv_name = [f for f in z.namelist() if f.endswith('.csv') and 'MetaData' not in f][0]
            df = pd.read_csv(z.open(csv_name), low_memory=False)
        
        # Standardize columns to uppercase to match StatCan's default export format
        df.columns = [c.strip().upper() for c in df.columns]
        
        # 1. Map Year from REF_DATE
        df['YEAR'] = pd.to_numeric(df['REF_DATE'].astype(str).str[:4])
        
        # 2. Identify LHINs from DGUID (Last 4 digits)
        df['HR_CODE'] = df['DGUID'].astype(str).str[-4:]
        df['LHIN'] = df['HR_CODE'].map(LHIN_MAP)
        
        # 3. Flexible Age Column Detection (Fixes the StopIteration error)
        # We look for any column that isn't a standard metadata field but contains 'AGE'
        standard_cols = ['REF_DATE', 'DGUID', 'UOM', 'SCALAR_FACTOR', 'VECTOR', 'COORDINATE', 'VALUE', 'STATUS', 'SYMBOL', 'TERMINATED', 'DECIMALS', 'YEAR', 'HR_CODE', 'LHIN']
        age_col = next((c for c in df.columns if "AGE" in c and c not in standard_cols), None)
        
        if not age_col:
            # Fallback: check all columns if the above fails
            age_col = next(c for c in df.columns if "AGE" in c)

        df['AGE_GROUP'] = df[age_col].map(STATCAN_AGE_MAP)
        
        # 4. Filter and Aggregate
        # We keep only rows that matched our LHIN and Age maps
        df = df[df['LHIN'].notna() & df['AGE_GROUP'].notna()]
        
        # Sum values (automatically handles all sexes/genders if present)
        out = df.groupby(['LHIN', 'YEAR', 'AGE_GROUP'], as_index=False)['VALUE'].sum()
        out.columns = ['LHIN', 'year', 'age_group', 'population']
        
        save_path = OUT_DIR / "population_by_age_lhin.csv"
        out.to_csv(save_path, index=False)
        log.info(f"✅ Success! File saved with {len(out)} rows to {save_path}")

    except Exception as e:
        log.error(f"Failed to process StatCan data: {e}")

if __name__ == "__main__":
    fetch_population_by_lhin()
