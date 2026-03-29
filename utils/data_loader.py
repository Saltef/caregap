import pandas as pd
import numpy as np
from pathlib import Path
import streamlit as st

# Explicit path resolution for Codespaces/Local
ROOT = Path(__file__).resolve().parent.parent
PROCESSED_FILE = ROOT / "data" / "processed" / "population_by_age_lhin.csv"
INPUT_DIR = ROOT / "inputData"

def get_projected_lhin_map(condition_name, target_year=2024):
    """
    Combines StatCan LHIN populations with Condition baseline rates.
    """
    # 1. Safety Check: Does the fetcher's output exist?
    if not PROCESSED_FILE.exists():
        st.error(f"🚨 Data file missing: {PROCESSED_FILE}. Run 'python3 fetch/statcan.py' first.")
        return pd.DataFrame()

    # 2. Load Data
    try:
        df_burden = pd.read_csv(INPUT_DIR / "layer2_current_burden.csv")
        df_pop = pd.read_csv(PROCESSED_FILE)
    except FileNotFoundError as e:
        st.error(f"🚨 Could not find input files: {e}")
        return pd.DataFrame()

    # 3. Extract Baseline Condition stats
    if condition_name not in df_burden['condition'].values:
        return pd.DataFrame()
    cond_stats = df_burden[df_burden['condition'] == condition_name].iloc[0]

    # 4. Filter for the Target Year
    df_year = df_pop[df_pop['year'] == target_year].copy()
    if df_year.empty:
        df_year = df_pop[df_pop['year'] == df_pop['year'].max()].copy()

    # 5. Create Regional Summary (Age Buckets)
    # The groups created by your fetcher: '0–14', '15–24', '25–44', '45–64', '65–74', '75–84', '85+'
    senior_groups = ['65–74', '75–84', '85+']
    df_year['is_senior'] = df_year['age_group'].isin(senior_groups)
    df_year['senior_population'] = np.where(df_year['is_senior'], df_year['population'], 0)

    agg_spec = {
        'population': 'sum',
        'senior_population': 'sum',
    }
    if 'lat' in df_year.columns:
        agg_spec['lat'] = 'first'
    if 'lon' in df_year.columns:
        agg_spec['lon'] = 'first'

    lhin_summary = (
        df_year.groupby('LHIN', as_index=False)
        .agg(agg_spec)
        .rename(columns={'population': 'pop_total', 'senior_population': 'pop_65_plus'})
    )

    # 6. Apply Proxy Weighting
    senior_weighted = ['COPD', 'Stroke', 'Pneumonia', 'Heart Failure']
    if condition_name in senior_weighted:
        total_seniors = lhin_summary['pop_65_plus'].sum()
        lhin_summary['weight'] = lhin_summary['pop_65_plus'] / total_seniors if total_seniors > 0 else 0
    else:
        total_pop = lhin_summary['pop_total'].sum()
        lhin_summary['weight'] = lhin_summary['pop_total'] / total_pop if total_pop > 0 else 0

    # 7. Final Projection
    lhin_summary['predicted_admissions'] = lhin_summary['weight'] * cond_stats['admissions']
    lhin_summary['predicted_cost'] = lhin_summary['weight'] * cond_stats['total_cost']
    
    return lhin_summary.drop(columns=['is_senior'], errors='ignore')
