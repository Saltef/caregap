import pandas as pd
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Data Manager", layout="wide")

st.markdown(
    """
<style>
    .source-card {
        background: #0d1117;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .source-title { color: #58a6ff; font-weight: 600; font-size: 1.1rem; }
    .source-meta { color: #8b949e; font-size: 0.85rem; }
    .badge {
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
    }
    .badge-missing { background: #490202; color: #ff7b72; border: 1px solid #6e1010; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("## Data Manager")
st.caption("Manage Ontario Health Intelligence datasets (Layers 1-4).")

input_dir = Path("inputData")
input_dir.mkdir(exist_ok=True)

file_map = {
    "Layer 1 - Population Demographics": "layer1_population_demographics.csv",
    "Layer 2 - Current Burden": "layer2_current_burden.csv",
    "Layer 3 - Predictive Trajectory": "layer3_predictive_trajectory.csv",
    "Layer 4 - Cost Analysis": "layer4_cost_analysis.csv",
    "Layer 4 - Metadata": "layer4_metadata.csv",
}

for label, filename in file_map.items():
    with st.expander(f"**{label}** - `{filename}`"):
        dest = input_dir / filename

        if dest.exists():
            try:
                df = pd.read_csv(dest)
                st.success(f"{len(df):,} rows loaded.")
                if "condition" in df.columns:
                    conditions = sorted(df["condition"].dropna().astype(str).unique().tolist())
                    if conditions:
                        st.info(f"Conditions: {', '.join(conditions)}")
                st.dataframe(df, use_container_width=True)
            except Exception as exc:
                st.error(f"Error reading CSV: {exc}")
        else:
            st.warning(f"{filename} is missing from `inputData/`.")

        uploaded = st.file_uploader(f"Replace {filename}", type=["csv"], key=filename)
        if uploaded is not None:
            try:
                test_df = pd.read_csv(uploaded)
                dest.write_bytes(uploaded.getvalue())
                st.success(f"Uploaded {filename} with {len(test_df):,} rows.")
                if st.button("Refresh Page", key=f"refresh_{filename}"):
                    st.rerun()
            except Exception as exc:
                st.error(f"Upload failed: {exc}")

st.divider()
st.markdown("### External Data Sync")
col_auto, col_manual = st.columns([1, 1], gap="large")

with col_auto:
    st.markdown("#### Statistics Canada (Layer 1)")
    if st.button("Fetch Latest StatCan Data", type="primary"):
        try:
            from fetch.statcan import fetch_all

            with st.spinner("Accessing StatsCan API..."):
                fetch_all()
            st.success("Layer 1 data updated.")
            st.rerun()
        except Exception as exc:
            st.error(f"StatsCan fetch failed: {exc}")

with col_manual:
    st.markdown("#### CIHI Manual Integration (Layer 2+)")
    st.info("Upload CIHI exports above to update burden and cost layers.")
