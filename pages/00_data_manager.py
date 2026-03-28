import json
import sys
from datetime import datetime, timezone
        badge = '<span class="badge badge-missing">✗ not loaded</span>'
        freshness = "Using synthetic data"

    method_badge = (
        '<span class="badge" style="background:#0d2d1a;color:#56d364;border:1px solid #238636;margin-left:6px">API auto-fetch</span>'
        if src["method"] == "auto" else
        '<span class="badge" style="background:#21262d;color:#8b949e;border:1px solid #30363d;margin-left:6px">Manual download</span>'
    )
    layer_badge = f'<span class="badge" style="background:#1b2a3d;color:#58a6ff;border:1px solid #1f6feb;margin-left:6px">{src["layer"]}</span>'

    st.markdown(f"""
    <div class="source-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
                <span class="source-title">{src["title"]}</span>
                {method_badge}{layer_badge}
                <div class="source-meta">{src["source"]}</div>
            </div>
            <div style="text-align:right">
                {badge}
                <div class="source-meta">{freshness}</div>
            </div>
        </div>
        {"" if not issues else f'<div style="margin-top:8px;font-size:0.75rem;color:#d29922">⚠ ' + " · ".join(issues) + "</div>"}
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Fetching & Uploading ─────────────────────────────────────────────────────
col_auto, col_manual = st.columns([1, 1], gap="large")

with col_auto:
    st.markdown("### 📡 Auto-fetch — Statistics Canada (Layer 1 & 3)")
    st.markdown("Pulls directly from the Stats Can Web Data Service.")

    fetch_clicked = st.button("🔄 Fetch from Stats Canada", type="primary", use_container_width=True)

    if fetch_clicked:
        from fetch.statcan import fetch_all
        with st.spinner("Connecting..."):
            results = fetch_all()
            st.success("Fetched successfully. Reload to see status.")
            st.rerun()

    if (ROOT / "data" / "processed" / "population_by_age_lhin.csv").exists():
        with st.expander("Preview — Population"):
            st.dataframe(pd.read_csv(ROOT / "data" / "processed" / "population_by_age_lhin.csv").head(10))

with col_manual:
    st.markdown("### 📥 Manual upload — CIHI (Layer 1 & 2)")
    
    # --- Layer 1: Providers ---
    tab1, tab2 = st.tabs(["L1: Health Providers", "L2: Hospitalizations"])
    
    with tab1:
        st.markdown('<p class="section-header">Physicians & Nurse Practitioners</p>', unsafe_allow_html=True)
        phy_file = st.file_uploader("Upload Physician Excel", type=["xlsx"], key="phy_up")
        if phy_file:
            save_path = ROOT / "data" / "raw" / phy_file.name
            save_path.write_bytes(phy_file.getbuffer())
            st.success("File saved. Processing logic pending implementation in cihi_loader.py")

    with tab2:
        st.markdown('<p class="section-header">Hospitalization & ER Visits (ACSC)</p>', unsafe_allow_html=True)
        st.markdown("""
        <div class="step"><div class="step-num">Step 1</div><div class="step-text">Go to <a href="https://www.cihi.ca/en/quick-stats" target="_blank">CIHI Quick Stats</a></div></div>
        <div class="step"><div class="step-num">Step 2</div><div class="step-text">Download <strong>Discharge Abstract Database (DAD)</strong> for Ontario</div></div>
        <div class="step"><div class="step-num">Step 3</div><div class="step-text">Upload the <code>.xlsx</code> file below.</div></div>
        """, unsafe_allow_html=True)
        
        hosp_file = st.file_uploader("Upload Hospitalization Excel", type=["xlsx"], key="hosp_up")
        
        if hosp_file:
            from utils.data_store import process_cihi_upload
            with st.spinner("Normalizing Hospitalization Data..."):
                if process_cihi_upload(hosp_file):
                    st.success("✓ Layer 2 Data Integrated!")
                    st.rerun()
                else:
                    st.error("Failed to parse CIHI file. Check column headers.")

st.divider()
st.markdown("### 🔬 Validation detail")
# (Validation logic remains same as your original)
