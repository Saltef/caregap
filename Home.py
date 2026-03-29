import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# --- CONFIGURATION ---
st.set_page_config(page_title="Ontario Health Intelligence", layout="wide")
INPUT_DIR = Path("inputData")

def load_all_data():
    """Helper to load all 4 layers if they exist."""
    layers = {}
    try:
        layers['l1'] = pd.read_csv(INPUT_DIR / "layer1_population_demographics.csv")
        layers['l2'] = pd.read_csv(INPUT_DIR / "layer2_current_burden.csv")
        layers['l3'] = pd.read_csv(INPUT_DIR / "layer3_predictive_trajectory.csv")
        layers['l4'] = pd.read_csv(INPUT_DIR / "layer4_cost_analysis.csv")
        return layers
    except FileNotFoundError as e:
        st.error(f"Missing data file: {e.filename}. Please upload it in the Data Manager.")
        return None

# --- APP LOGIC ---
data = load_all_data()

if data:
    st.title("🏥 Ontario Health Intelligence Portal")
    
    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Global Filters")
    all_conditions = data['l2']['condition'].unique().tolist()
    selected_condition = st.sidebar.selectbox("Select Condition Focus", ["All Conditions"] + all_conditions)

    # --- TOP LEVEL METRICS (Layer 1 & 2) ---
    st.subheader("Provincial Snapshot (2024)")
    col1, col2, col3, col4 = st.columns(4)
    
    ont_pop = data['l1'].iloc[0]['population_2024']
    total_ed = data['l2']['ed_visits'].sum()
    total_avoidable_cost = data['l2']['avoidable_cost'].sum()
    avg_gap = data['l2']['care_gap_score'].mean()

    col1.metric("Ontario Population", f"{ont_pop/1e6:.1f}M")
    col2.metric("Annual ED Visits", f"{total_ed:,.0f}")
    col3.metric("Avoidable Cost", f"${total_avoidable_cost/1e6:.1f}M", delta_color="inverse")
    col4.metric("Avg Care Gap Score", f"{avg_gap:.1f}")

    st.divider()

    # --- CONDITION DEEP DIVE ---
    if selected_condition != "All Conditions":
        c_data = data['l2'][data['l2']['condition'] == selected_condition].iloc[0]
        c_cost = data['l4'][data['l4']['condition'] == selected_condition].iloc[0]
        
        st.header(f"Analysis: {selected_condition}")
        
        tab_burden, tab_forecast, tab_roi = st.tabs(["Current Burden", "10-Year Forecast", "ROI Analysis"])
        
        with tab_burden:
            m1, m2, m3 = st.columns(3)
            m1.metric("Wait Weeks (ON)", f"{c_data['specialist_wait_weeks_ontario']} wks")
            m2.metric("Primary Specialty", c_data['primary_specialty'])
            m3.metric("Avoidability %", f"{c_data['avoidability_pct']*100:.0%}")
            
            # Comparison Chart
            st.plotly_chart(px.bar(data['l2'], x='condition', y='care_gap_score', 
                                   title="Care Gap Score Comparison", color='condition'))

        with tab_forecast:
            st.subheader(f"Projected Admissions to 2034")
            traj = data['l3'][data['l3']['condition'] == selected_condition]
            fig = px.line(traj, x='year', y='admissions', markers=True, 
                          title=f"Growth Trajectory ({selected_condition})")
            st.plotly_chart(fig, use_container_width=True)

        with tab_roi:
            st.subheader("Investment & Savings Potential")
            r1, r2 = st.columns(2)
            r1.metric("5-Year Savings", f"${c_cost['savings_5yr']:,.0f}")
            r2.metric("ROI Ratio", f"{c_cost['roi_5yr']}:1")
            
            st.info(f"Potential savings per admission: **${c_cost['potential_savings_per_admission']:,.0f}**")

    else:
        # Overview visualization if "All Conditions" is selected
        st.subheader("Condition Heatmap: Cost vs. Avoidability")
        fig_map = px.scatter(data['l2'], x="ed_visits", y="avoidable_cost", 
                             size="admissions", color="condition",
                             hover_name="condition", log_x=True,
                             title="High Volume vs. High Cost Opportunities")
        st.plotly_chart(fig_map, use_container_width=True)

else:
    st.info("👋 Welcome! Use the **Data Manager** in the sidebar to upload your CSV files and begin.")
