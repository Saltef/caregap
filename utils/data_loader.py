import pandas as pd
from pathlib import Path

INPUT_DIR = Path("inputData")

def get_master_dataframe():
    """
    Joins Layer 2 (Current Burden) and Layer 4 (Cost Analysis) 
    to create a comprehensive view of the health landscape.
    """
    try:
        # Load Layer 2 (Anchor)
        df_burden = pd.read_csv(INPUT_DIR / "layer2_current_burden.csv")
        
        # Load Layer 4 (ROI/Savings)
        df_cost = pd.read_csv(INPUT_DIR / "layer4_cost_analysis.csv")
        
        # Join on 'condition' since both files use it as the primary key
        # We use a left join to keep all burden data even if cost analysis is missing
        master_df = pd.merge(df_burden, df_cost, on="condition", how="left", suffixes=('', '_l4'))
        
        return master_df
    except Exception as e:
        print(f"Error joining datasets: {e}")
        return pd.DataFrame()

def get_trajectories(condition_name=None):
    """
    Returns the growth projections from Layer 3.
    """
    df = pd.read_csv(INPUT_DIR / "layer3_predictive_trajectory.csv")
    if condition_name:
        return df[df['condition'] == condition_name]
    return df

def get_demographics():
    """
    Returns the provincial stats from Layer 1.
    """
    return pd.read_csv(INPUT_DIR / "layer1_population_demographics.csv")
