import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_loader import get_age_proxy_data

st.set_page_config(page_title="Ontario Health Intel", layout="wide")

st.title("🏥 Ontario Health: Age-Proxy Regional Mapping")
st.markdown("Using **StatCan Demographic Distributions** to proxy provincial health burdens.")

# Sidebar Selection
df_burden = pd.read_csv("inputData/layer2_current_burden.csv")
condition = st.sidebar.selectbox("Select Condition", df_burden['condition'].unique())

# Process Data via Proxy Engine
mapped_df = get_age_proxy_data(condition)

# --- VISUALIZATION ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"Projected {condition} Hotspots")
    # Using a Bar Chart as a proxy for a Map until GeoJSON is integrated
    fig = px.bar(
        mapped_df.sort_values('predicted_admissions', ascending=False),
        x='region', 
        y='predicted_admissions',
        color='predicted_cost',
        labels={'predicted_admissions': 'Estimated Admissions'},
        color_continuous_scale='Reds',
        template='plotly_dark'
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Regional Totals")
    st.dataframe(
        mapped_df[['region', 'predicted_admissions', 'predicted_cost']]
        .style.format({'predicted_cost': '${:,.0f}', 'predicted_admissions': '{:.0f}'})
    )

st.divider()
st.info("💡 **Methodology:** This view applies provincial baseline rates from Layer 2 to StatCan regional age counts. Regions with higher 65+ populations are weighted more heavily for age-sensitive conditions.")
