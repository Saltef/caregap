import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

def get_projected_data(year, scenario, age_group):
    # 1. Load current LHIN populations
    df_lhin = pd.read_csv(DATA_DIR / "processed/population_by_age_lhin.csv")
    
    # 2. Load Provincial Projections
    df_proj = pd.read_csv(DATA_DIR / "processed/population_projections.csv")
    
    # 3. Load Coordinates
    coords = pd.read_csv(DATA_DIR / "static/lhin_coords.csv")
    
    # Calculate Growth Multiplier from Projections
    # (Provincial Pop in Target Year / Provincial Pop in Current Year)
    current_year = 2024 # Or latest in your data
    base_pop = df_proj[(df_proj['year'] == current_year) & 
                       (df_proj['age_group'] == age_group)]['population'].sum()
    target_pop = df_proj[(df_proj['year'] == year) & 
                        (df_proj['scenario_label'] == scenario) & 
                        (df_proj['age_group'] == age_group)]['population'].sum()
    
    multiplier = target_pop / base_pop if base_pop > 0 else 1.0

    # Apply multiplier to current LHIN data
    df_lhin['projected_pop'] = df_lhin['population'] * multiplier
    
    # Merge with coordinates for the map
    df_final = df_lhin.merge(coords, left_on='LHIN', right_on='lhin_name')
    return df_final[df_final['age_group'] == age_group]
