import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# ──────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────
st.set_page_config(
    page_title="Ontario Health: 2043 Projections",
    page_icon="📈",
    layout="wide",
)

# Custom CSS for a dark, data-focused theme
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
.main { background: #0d1117; }
.page-title { font-size: 1.6rem; font-weight: 600; color: #e6edf3; margin-bottom: 0; }
.page-sub { font-size: 0.85rem; color: #7d8590; margin-bottom: 20px; }
.section-label { font-size: 0.7rem; font-weight: 600; color: #7d8590; text-transform: uppercase; letter-spacing: 0.1em; margin: 15px 0 5px; }
.stat-card { background: #161b22; border: 1px solid #21262d; border-radius: 10px; padding: 15px; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────
# DATA LAYER: BASELINE & PROJECTION LOGIC
# ──────────────────────────────────────────
LHIN_BASE = {
    "Erie St. Clair":      {"lat": 42.32, "lon": -82.55, "pop_2024": 650_000,   "growth": 0.012},
    "South West":          {"lat": 42.98, "lon": -81.25, "pop_2024": 1_000_000, "growth": 0.015},
    "Waterloo Wellington": {"lat": 43.55, "lon": -80.50, "pop_2024": 850_000,   "growth": 0.021},
    "Hamilton Niagara":    {"lat": 43.18, "lon": -79.90, "pop_2024": 1_500_000, "growth": 0.011},
    "Central West":        {"lat": 43.72, "lon": -79.90, "pop_2024": 950_000,   "growth": 0.025},
    "Mississauga Halton":  {"lat": 43.60, "lon": -79.65, "pop_2024": 1_300_000, "growth": 0.018},
    "Toronto Central":     {"lat": 43.67, "lon": -79.39, "pop_2024": 1_250_000, "growth": 0.014},
    "Central":             {"lat": 43.83, "lon": -79.50, "pop_2024": 1_900_000, "growth": 0.022},
    "Central East":        {"lat": 44.15, "lon": -78.90, "pop_2024": 1_700_000, "growth": 0.019},
    "South East":          {"lat": 44.52, "lon": -76.55, "pop_2024": 520_000,   "growth": 0.008},
    "Champlain":           {"lat": 45.30, "lon": -75.70, "pop_2024": 1_400_000, "growth": 0.016},
    "North Simcoe":        {"lat": 44.85, "lon": -79.60, "pop_2024": 500_000,   "growth": 0.020},
    "North East":          {"lat": 46.80, "lon": -81.00, "pop_2024": 560_000,   "growth": 0.003},
    "North West":          {"lat": 49.40, "lon": -86.60, "pop_2024": 240_000,   "growth": 0.001},
}

@st.cache_data
def get_projections(target_year, scenario_mult):
    rows = []
    years_out = target_year - 2024
    for name, data in LHIN_BASE.items():
        # Compound growth logic
        effective_growth = data['growth'] * scenario_mult
        projected_pop = int(data['pop_2024'] * ((1 + effective_growth) ** years_out))
        growth_amt = projected_pop - data['pop_2024']
        growth_pct = (growth_amt / data['pop_2024']) * 100
        
        rows.append({
            "LHIN": name, "lat": data['lat'], "lon": data['lon'],
            "Base Pop": data['pop_2024'],
            "Projected Pop": projected_pop,
            "Growth": growth_amt,
            "Growth %": round(growth_pct, 1)
        })
    return pd.DataFrame(rows)

# ──────────────────────────────────────────
# SIDEBAR CONTROLS (Layer 3 Focus)
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown("### Projection Settings")
    target_year = st.slider("Target Year", 2024, 2043, 2035)
    scenario = st.radio("Growth Scenario", 
                        ["Low (Slow Aging)", "Reference (StatsCan)", "High (Accelerated)"], 
                        index=1)
    
    # Map scenario to multipliers
    scenario_map = {"Low (Slow Aging)": 0.7, "Reference (StatsCan)": 1.0, "High (Accelerated)": 1.4}
    df_proj = get_projections(target_year, scenario_map[scenario])

# ──────────────────────────────────────────
# MAIN UI
# ──────────────────────────────────────────
st.markdown('<div class="page-title">Ontario Population Projection Dashboard</div>', unsafe_allow_html=True)
st.markdown(f'<div class="page-sub">Projecting growth from 2024 to {target_year} based on {scenario} scenario.</div>', unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
with m1:
    total_pop = df_proj["Projected Pop"].sum()
    st.metric("Total Ontario Pop", f"{total_pop/1e6:.2f}M", f"{((total_pop/sum(d['pop_2024'] for d in LHIN_BASE.values()))-1)*100:.1f}%")
with m2:
    top_growth = df_proj.loc[df_proj["Growth %"].idxmax()]
    st.metric("Highest Growth LHIN", top_growth["LHIN"], f"{top_growth['Growth %']}%")
with m3:
    st.metric("Target Year", target_year)

# ──────────────────────────────────────────
# MAP: VISUALIZING GROWTH
# ──────────────────────────────────────────
fig_map = px.scatter_mapbox(
    df_proj, lat="lat", lon="lon",
    size="Projected Pop", color="Growth %",
    hover_name="LHIN",
    hover_data={"lat": False, "lon": False, "Projected Pop": ":,d", "Growth %": ":.1f%"},
    color_continuous_scale="Viridis",
    size_max=40, zoom=4.5,
    mapbox_style="carto-darkmatter"
)
fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor="#0d1117", height=500)

st.plotly_chart(fig_map, use_container_width=True)

# ──────────────────────────────────────────
# DETAIL TABLE
# ──────────────────────────────────────────
st.markdown('<p class="section-label">LHIN Projection Summary</p>', unsafe_allow_html=True)
st.dataframe(
    df_proj.sort_values("Growth %", ascending=False),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Projected Pop": st.column_config.NumberColumn(format="%d"),
        "Growth %": st.column_config.ProgressColumn(min_value=0, max_value=50, format="%.1f%%")
    }
)
