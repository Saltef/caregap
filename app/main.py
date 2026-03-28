import streamlit as st
import leafmap.foliumap as leafmap
from data_loader import load_and_clean_data, calculate_service_pressure

st.set_page_config(layout="wide", page_title="Ontario Health Intel")

st.title("Layer 1: Population Density & Service Trajectory")

# 1. Sidebar Controls
with st.sidebar:
    st.header("Parameters")
    year = st.slider("Select Projection Year", 2024, 2051, 2024)
    metric = st.selectbox("Select Metric", ["Weighted Demand", "Physician Gap", "Aged Density"])

# 2. Data Processing
data = load_and_clean_data()
pressure_df = calculate_service_pressure(data, year)

# 3. Map Rendering
m = leafmap.Map(center=[44.0, -79.0], zoom=7)

# Load CSD Boundaries and Join with our calculated Pressure Score
gdf = gpd.read_file("data/geography/ontario_csd.geojson")
merged = gdf.merge(pressure_df, left_on="CSDUID", right_on="CSDUID")

m.add_data(
    merged, 
    column="Demand_Score", 
    scheme="Quantiles", 
    cmap="YlOrRd", 
    legend_title=f"Medical Demand ({year})"
)

st_data = m.to_streamlit(height=700)
