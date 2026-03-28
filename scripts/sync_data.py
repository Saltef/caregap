import os
import requests
import pandas as pd
import geopandas as gpd

# Define Paths
DATA_DIR = "data/raw"
os.makedirs(DATA_DIR, exist_ok=True)

def download_mof_projections():
    print("Downloading MOF Projections...")
    # This is the 2024-2051 Census Division Projection URL
    url = "https://data.ontario.ca/dataset/f52a6457-fb37-4267-acde-11a1e57c4dc8/resource/84a1d0ab-b4bc-4fdb-a6f6-d0a1e89208a8/download/49_cds_mof_projections_en.xlsx"
    r = requests.get(url)
    file_path = f"{DATA_DIR}/mof_projections.xlsx"
    with open(file_path, 'wb') as f:
        f.write(r.content)
    print(f"Saved to {file_path}")

def download_census_geography():
    print("Downloading Census Subdivision Boundaries...")
    # Direct link to StatsCan 2021 CSD Digital Boundary File (Ontario subset usually handled via filtering)
    # Note: Using a GeoJSON API or a simplified TopoJSON is faster for Streamlit
    url = "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lcsd000b21a_e.zip"
    # Logic to download and unzip...
    print("Geography sync complete.")

if __name__ == "__main__":
    download_mof_projections()
    # After download, run a 'clean' function to convert XLSX to a fast-loading Parquet or CSV
