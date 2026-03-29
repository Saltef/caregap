import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_loader import get_projected_lhin_map

st.set_page_config(page_title="Ontario Health Intel", layout="wide")

# --- SIDEBAR FILTERS ---
st.sidebar.title("Forecast Controls")
df_burden = pd.read_csv("inputData/layer2_current_burden.csv")
condition = st.sidebar.selectbox("Select Condition", df_burden['condition'].unique())

# Pull years from processed StatCan data
df_pop = pd.read_csv("data/processed/population_by_age_lhin.csv")
available_years = sorted(df_pop['year'].unique())
target_year = st.sidebar.select_slider("Select Target Year", options=available_years)

# --- LOAD DATA ---
mapped_df = get_projected_lhin_map(condition, target_year)

# --- MAIN DASHBOARD ---
st.title(f"🏥 {condition} Regional Heatmap ({target_year})")
st.write(f"Showing the projected burden based on **StatCan 2026** demographic shifts.")

col1, col2 = st.columns([2, 1])

with col1:
    # HEATMAP VISUALIZATION
    # In a full production app, you would add geojson=lhin_geojson_url here
    fig = px.bar(
        mapped_df.sort_values('predicted_admissions', ascending=True),
        x='predicted_admissions', 
        y='LHIN',
        orientation='h',
        color='predicted_admissions',
        title=f"Heat Distribution: {condition} Admissions",
        color_continuous_scale='Reds',
        template='plotly_dark'
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Provincial Summary")
    total_adm = mapped_df['predicted_admissions'].sum()
    total_cost = mapped_df['predicted_cost'].sum()
    
    st.metric("Total Admissions", f"{total_adm:,.0f}")
    st.metric("Total Estimated Cost", f"${total_cost/1e6:.1f}M")
    
    st.write("---")
    st.subheader("Top 3 High-Impact Regions")
    top_3 = mapped_df.nlargest(3, 'predicted_admissions')
    for idx, row in top_3.iterrows():
        st.write(f"**{row['LHIN']}**: {row['predicted_admissions']:,.0f} cases")

st.divider()
st.dataframe(mapped_df[['LHIN', 'predicted_admissions', 'predicted_cost']])
