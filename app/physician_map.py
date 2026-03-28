import streamlit as st
import leafmap.foliumap as leafmap

st.title("Ontario Physician Access Dashboard")

# 1. Select Geography Level
view_level = st.radio("Select View Level", ["City (CSD)", "LHIN / Region"])

# 2. Year Slider (2024-2051)
year = st.slider("Select Year", 2024, 2051)

# 3. Load Data based on selection
if view_level == "City (CSD)":
    geojson_path = "data/geography/ontario_csd.json"
    data_col = "Physicians_per_1000"
else:
    geojson_path = "data/geography/ontario_lhin.json"
    data_col = "LHIN_Access_Score"

# 4. Render Map
m = leafmap.Map(center=[44, -79], zoom=6)
m.add_geojson(geojson_path, layer_name=view_level)

# Add Physician points as a Heatmap toggle
if st.checkbox("Show Clinic Heatmap"):
    m.add_heatmap("data/processed/physician_points.csv", x="lat", y="lon", value="count")

m.to_streamlit()
