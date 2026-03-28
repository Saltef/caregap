import os
import requests
import pandas as pd
import zipfile
import io

# 1. Configuration
MOF_URL = "https://data.ontario.ca/dataset/f52a6457-fb37-4267-acde-11a1e57c4dc8/resource/84a1d0ab-b4bc-4fdb-a6f6-d0a1e89208a8/download/49_cds_mof_projections_en.xlsx"
CSD_GEO_URL = "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lcsd000b21a_e.zip"
RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"

def setup_dirs():
    for d in [RAW_DIR, PROCESSED_DIR]:
        os.makedirs(d, exist_ok=True)

def fetch_mof_data():
    print("Fetching MOF Projections...")
    resp = requests.get(MOF_URL)
    # Note: Using openpyxl as engine for the Excel download
    df = pd.read_excel(io.BytesIO(resp.content), sheet_name=None)
    
    # Logic to merge sheets and 'melt' years 2024-2051 into a single column
    # For now, we save the raw version
    full_df = pd.concat(df.values())
    full_df.to_csv(f"{PROCESSED_DIR}/mof_projections_long.csv", index=False)
    print("MOF data processed.")

def fetch_geography():
    print("Fetching StatCan Boundaries...")
    r = requests.get(CSD_GEO_URL)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(f"{RAW_DIR}/geography")
    print("Geography downloaded.")

if __name__ == "__main__":
    setup_dirs()
    fetch_mof_data()
    fetch_geography()
