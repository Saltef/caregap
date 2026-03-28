"""
Ontario Health Intelligence Platform — Layer 1
Population Density × Care Supply · Interactive Map

Run:     streamlit run ontario_health_l1.py
Install: pip install streamlit plotly pandas numpy

Data: Synthetic data modelled after public sources:
  - Statistics Canada Census 2021 (Table 98-10-0007-01)
  - Statistics Canada Population Projections (Table 17-10-0057-01)
  - CIHI Physicians in Canada 2022 report
  Replace DATA LAYER section with real loaders when data is available.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# ──────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────
st.set_page_config(
    page_title="Ontario Health Intelligence",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }

.main { background: #0d1117; }
[data-testid="stAppViewContainer"] { background: #0d1117; }
[data-testid="stHeader"] { background: #0d1117; }

.block-container { padding: 1rem 1.5rem 1rem 1.5rem !important; }

.page-title {
    font-size: 1.4rem; font-weight: 600; color: #e6edf3;
    letter-spacing: -0.02em; margin-bottom: 0;
}
.page-sub {
    font-size: 0.78rem; color: #7d8590; margin-top: 2px; margin-bottom: 12px;
}
.layer-badge {
    display: inline-block; background: #1f6feb22; color: #58a6ff;
    border: 1px solid #1f6feb55; border-radius: 4px;
    font-size: 0.68rem; font-weight: 600; letter-spacing: 0.08em;
    padding: 2px 8px; text-transform: uppercase; margin-bottom: 8px;
}

.stat-card {
    background: #161b22; border: 1px solid #21262d;
    border-radius: 10px; padding: 14px 16px;
}
.stat-label {
    font-size: 0.7rem; font-weight: 500; color: #7d8590;
    text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 4px;
}
.stat-value {
    font-size: 1.6rem; font-weight: 600; color: #e6edf3; line-height: 1;
}
.stat-delta { font-size: 0.75rem; margin-top: 4px; }
.delta-good { color: #3fb950; }
.delta-warn { color: #d29922; }
.delta-bad  { color: #f85149; }

.section-label {
    font-size: 0.68rem; font-weight: 600; color: #7d8590;
    text-transform: uppercase; letter-spacing: 0.09em;
    margin: 14px 0 6px;
}

.gap-pill {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 600;
}
.gap-good   { background: #238636; color: #aff5b4; }
.gap-med    { background: #9e6a03; color: #ffd271; }
.gap-bad    { background: #8e1519; color: #ffa198; }

.map-hint {
    font-size: 0.72rem; color: #7d8590;
    text-align: center; margin-top: 4px;
}

.provider-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 0; border-bottom: 1px solid #21262d;
}
.provider-name { font-size: 0.82rem; color: #c9d1d9; }
.provider-rate { font-size: 0.82rem; font-weight: 600; color: #e6edf3; }
.provider-bar-wrap { width: 90px; height: 6px; background: #21262d; border-radius: 3px; }
.provider-bar { height: 6px; border-radius: 3px; }

[data-testid="stPlotlyChart"] { border-radius: 10px; overflow: hidden; }
div[data-testid="stMetric"] { background: #161b22; border: 1px solid #21262d; border-radius: 10px; padding: 12px 16px; }
div[data-testid="stMetric"] label { color: #7d8590 !important; font-size: 0.7rem !important; }
div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #e6edf3 !important; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────
# DATA LAYER
# ──────────────────────────────────────────
AGE_GROUPS = ["0–14", "15–24", "25–44", "45–64", "65–74", "75–84", "85+"]
AGE_COLORS = ["#58a6ff","#79c0ff","#388bfd","#1f6feb","#d29922","#f0883e","#f85149"]

LHIN_DATA = {
    "Erie St. Clair":                   dict(lat=42.32, lon=-82.55, pop=542_000,   type="mixed"),
    "South West":                       dict(lat=42.98, lon=-81.25, pop=503_000,   type="rural"),
    "Waterloo Wellington":              dict(lat=43.55, lon=-80.50, pop=634_000,   type="suburban"),
    "Hamilton Niagara Haldimand Brant": dict(lat=43.18, lon=-79.90, pop=1_497_000, type="urban"),
    "Central West":                     dict(lat=43.72, lon=-79.90, pop=882_000,   type="suburban"),
    "Mississauga Halton":               dict(lat=43.60, lon=-79.65, pop=1_218_000, type="urban"),
    "Toronto Central":                  dict(lat=43.67, lon=-79.39, pop=1_214_000, type="urban"),
    "Central":                          dict(lat=43.83, lon=-79.50, pop=1_812_000, type="urban"),
    "Central East":                     dict(lat=44.15, lon=-78.90, pop=1_403_000, type="suburban"),
    "South East":                       dict(lat=44.52, lon=-76.55, pop=491_000,   type="rural"),
    "Champlain":                        dict(lat=45.30, lon=-75.70, pop=1_298_000, type="urban"),
    "North Simcoe Muskoka":             dict(lat=44.85, lon=-79.60, pop=471_000,   type="rural"),
    "North East":                       dict(lat=46.80, lon=-81.00, pop=563_000,   type="northern"),
    "North West":                       dict(lat=49.40, lon=-86.60, pop=242_000,   type="northern"),
}

AGE_WEIGHTS = {
    "urban":    [0.155,0.120,0.290,0.240,0.100,0.065,0.030],
    "suburban": [0.175,0.115,0.275,0.240,0.105,0.065,0.025],
    "mixed":    [0.168,0.118,0.268,0.248,0.108,0.065,0.025],
    "rural":    [0.155,0.110,0.245,0.270,0.125,0.070,0.025],
    "northern": [0.160,0.118,0.260,0.278,0.110,0.055,0.019],
}
GP_DENSITY       = {"urban":1.18,"suburban":0.98,"mixed":0.88,"rural":0.72,"northern":0.58}
SPECIALIST_DENSITY={"urban":1.55,"suburban":0.92,"mixed":0.75,"rural":0.45,"northern":0.38}
NP_DENSITY       = {"urban":0.35,"suburban":0.28,"mixed":0.25,"rural":0.22,"northern":0.30}

BENCHMARK_GP   = 1.05
BENCHMARK_SPEC = 1.10
BENCHMARK_NP   = 0.30

PHU_MAP = {
    "Erie St. Clair":   ["Windsor-Essex", "Chatham-Kent", "Lambton"],
    "South West":       ["Elgin-St. Thomas", "Middlesex-London", "Huron Perth", "Oxford"],
    "Waterloo Wellington": ["Waterloo Region", "Wellington-Dufferin-Guelph"],
    "Hamilton Niagara Haldimand Brant": ["Hamilton", "Niagara", "Haldimand-Norfolk", "Brant"],
    "Central West":     ["Peel (north)", "Halton Hills"],
    "Mississauga Halton": ["Halton", "Mississauga"],
    "Toronto Central":  ["Toronto"],
    "Central":          ["York Region", "South Simcoe"],
    "Central East":     ["Durham", "Peterborough", "Haliburton Kawartha"],
    "South East":       ["Kingston Frontenac Lennox", "Leeds Grenville", "Hastings Prince Edward"],
    "Champlain":        ["Ottawa", "Eastern Ontario", "Renfrew"],
    "North Simcoe Muskoka": ["North Bay Parry Sound", "Simcoe Muskoka"],
    "North East":       ["Sudbury", "Porcupine", "Algoma", "Timiskaming"],
    "North West":       ["Thunder Bay", "Northwestern"],
}

@st.cache_data
def build_lhin_df():
    rng = np.random.default_rng(42)
    rows = []
    for lhin, meta in LHIN_DATA.items():
        t = meta["type"]; pop = meta["pop"]
        w = np.array(AGE_WEIGHTS[t]) * rng.uniform(0.97,1.03,7)
        w /= w.sum()
        age_pops = (w * pop).astype(int)

        gp_r   = GP_DENSITY[t]        * rng.uniform(0.92,1.08)
        spec_r = SPECIALIST_DENSITY[t] * rng.uniform(0.92,1.08)
        np_r   = NP_DENSITY[t]        * rng.uniform(0.92,1.08)

        demand = float(np.dot(w, [0.5,0.6,0.8,1.0,1.5,2.0,2.5]))
        supply = (gp_r/BENCHMARK_GP)*0.55 + (spec_r/BENCHMARK_SPEC)*0.35 + (np_r/BENCHMARK_NP)*0.10
        gap    = demand / supply

        rows.append({
            "LHIN": lhin, "lat": meta["lat"], "lon": meta["lon"],
            "type": t, "population": pop,
            **{f"pop_{ag}": int(age_pops[i]) for i,ag in enumerate(AGE_GROUPS)},
            "gp_per_1000":   round(gp_r,3),
            "spec_per_1000": round(spec_r,3),
            "np_per_1000":   round(np_r,3),
            "gp_count":   int(gp_r*pop/1000),
            "spec_count": int(spec_r*pop/1000),
            "np_count":   int(np_r*pop/1000),
            "demand_score": round(demand,3),
            "supply_score": round(supply,3),
            "gap_score":    round(gap,3),
            "pct_65plus":   round((age_pops[4]+age_pops[5]+age_pops[6])/pop*100,1),
        })
    return pd.DataFrame(rows)

df = build_lhin_df()

# ──────────────────────────────────────────
# STATE
# ──────────────────────────────────────────
if "selected_lhin" not in st.session_state:
    st.session_state.selected_lhin = None
if "map_mode" not in st.session_state:
    st.session_state.map_mode = "Gap score"

# ──────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────
top_left, top_right = st.columns([3,1])
with top_left:
    st.markdown('<div class="layer-badge">Layer 1</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-title">Ontario Population & Care Supply</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">14 LHINs · Population by age cohort × provider density · click any region to explore</div>', unsafe_allow_html=True)
with top_right:
    map_mode = st.selectbox(
        "Map colour",
        ["Gap score","GP density","Specialist density","NP density","% 65+ population","Total population"],
        key="map_mode_select",
        label_visibility="collapsed"
    )

# ──────────────────────────────────────────
# MAP CONFIG
# ──────────────────────────────────────────
COLOR_MAP = {
    "Gap score":            ("gap_score",    "Gap score (demand/supply)",  "RdYlGn_r", None, None),
    "GP density":           ("gp_per_1000",  "GPs per 1,000 pop",          "YlGn",     0, 1.4),
    "Specialist density":   ("spec_per_1000","Specialists per 1,000 pop",  "Blues",    0, 2.0),
    "NP density":           ("np_per_1000",  "NPs per 1,000 pop",          "Purples",  0, 0.5),
    "% 65+ population":     ("pct_65plus",   "% aged 65+",                 "OrRd",     0, 25),
    "Total population":     ("population",   "Total population",           "Viridis",  None, None),
}

col_field, col_label, col_scale, c_min, c_max = COLOR_MAP[map_mode]

plot_df = df.copy()
plot_df["size_norm"] = np.sqrt(plot_df["population"] / plot_df["population"].max()) * 38 + 10
plot_df["tooltip_pop"] = plot_df["population"].apply(lambda x: f"{x:,}")
plot_df["tooltip_gap"] = plot_df["gap_score"].apply(lambda x: f"{x:.2f}")
plot_df["tooltip_gp"]  = plot_df["gp_per_1000"].apply(lambda x: f"{x:.2f}")
plot_df["tooltip_65"]  = plot_df["pct_65plus"].apply(lambda x: f"{x:.1f}%")
plot_df["gap_label"] = plot_df["gap_score"].apply(
    lambda x: "Well served" if x < 0.95 else ("Moderate gap" if x < 1.15 else "Undersupplied")
)

# Highlight selected
if st.session_state.selected_lhin:
    plot_df["_alpha"] = plot_df["LHIN"].apply(
        lambda l: 1.0 if l == st.session_state.selected_lhin else 0.45
    )
else:
    plot_df["_alpha"] = 1.0

fig_map = go.Figure()

for _, row in plot_df.iterrows():
    is_sel = (row["LHIN"] == st.session_state.selected_lhin)
    val = row[col_field]

    # Colour mapping
    if col_scale == "RdYlGn_r":
        norm = min(max((val - 0.7) / 0.8, 0), 1)
        r = int(255 * min(norm * 2, 1))
        g = int(255 * min((1-norm)*2, 1))
        color = f"rgba({r},{g},60,{row['_alpha']})"
    elif col_scale == "YlGn":
        norm = min(max((val - (c_min or 0)) / ((c_max or 1.4) - (c_min or 0)), 0), 1)
        g = int(120 + 120 * norm); r = int(200 - 160*norm)
        color = f"rgba({r},{g},80,{row['_alpha']})"
    elif col_scale == "Blues":
        norm = min(max((val - (c_min or 0)) / ((c_max or 2) - (c_min or 0)), 0), 1)
        b = int(120 + 120 * norm); r = int(30 + 80*(1-norm))
        color = f"rgba({r},{int(100+100*norm)},{b},{row['_alpha']})"
    elif col_scale == "Purples":
        norm = min(max((val - (c_min or 0)) / ((c_max or 0.5) - (c_min or 0)), 0), 1)
        color = f"rgba({int(80+100*norm)},60,{int(140+100*norm)},{row['_alpha']})"
    elif col_scale == "OrRd":
        norm = min(max((val - (c_min or 0)) / ((c_max or 25) - (c_min or 0)), 0), 1)
        color = f"rgba({int(200+50*norm)},{int(100-80*norm)},40,{row['_alpha']})"
    else:
        norm = min(max((val - df[col_field].min()) / (df[col_field].max() - df[col_field].min() + 1e-9), 0), 1)
        color = f"rgba(80,{int(80+160*norm)},{int(180-100*norm)},{row['_alpha']})"

    fig_map.add_trace(go.Scattermapbox(
        lat=[row["lat"]], lon=[row["lon"]],
        mode="markers",
        marker=dict(
            size=row["size_norm"] * (1.25 if is_sel else 1.0),
            color=color,
            opacity=1,
        ),
        name=row["LHIN"],
        customdata=[[
            row["LHIN"], row["tooltip_pop"], row["tooltip_gap"],
            row["tooltip_gp"], row["tooltip_65"], row["gap_label"],
            row["type"].title(), f"{row['spec_per_1000']:.2f}",
        ]],
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Population: %{customdata[1]}<br>"
            "Gap score: %{customdata[2]} — %{customdata[5]}<br>"
            "GPs / 1,000: %{customdata[3]}<br>"
            "Specialists / 1,000: %{customdata[7]}<br>"
            "65+ population: %{customdata[4]}<br>"
            "Region type: %{customdata[6]}"
            "<extra></extra>"
        ),
        showlegend=False,
    ))

    # Ring for selected
    if is_sel:
        fig_map.add_trace(go.Scattermapbox(
            lat=[row["lat"]], lon=[row["lon"]],
            mode="markers",
            marker=dict(size=row["size_norm"]*1.55, color="rgba(255,255,255,0)", opacity=1,
                        symbol="circle"),
            hoverinfo="skip", showlegend=False,
        ))
        # White ring via second invisible marker with large border — use annotation instead
        fig_map.add_trace(go.Scattermapbox(
            lat=[row["lat"]], lon=[row["lon"]],
            mode="text",
            text=["●"],
            textfont=dict(size=row["size_norm"]*1.9, color="rgba(255,255,255,0.9)"),
            hoverinfo="skip", showlegend=False,
        ))

    # Label
    fig_map.add_trace(go.Scattermapbox(
        lat=[row["lat"]+0.18], lon=[row["lon"]],
        mode="text",
        text=[row["LHIN"].split()[0]],
        textfont=dict(size=10, color="rgba(230,237,243,0.75)"),
        hoverinfo="skip", showlegend=False,
    ))

fig_map.update_layout(
    mapbox=dict(
        style="carto-darkmatter",
        center=dict(lat=46.0, lon=-82.0),
        zoom=4.8,
    ),
    margin=dict(l=0, r=0, t=0, b=0),
    paper_bgcolor="#0d1117",
    plot_bgcolor="#0d1117",
    height=520,
    clickmode="event+select",
)

# ──────────────────────────────────────────
# LAYOUT: MAP + DETAIL PANEL
# ──────────────────────────────────────────
map_col, detail_col = st.columns([3, 2], gap="medium")

with map_col:
    clicked = st.plotly_chart(
        fig_map,
        use_container_width=True,
        key="main_map",
        on_select="rerun",
        selection_mode="points",
    )
    st.markdown('<p class="map-hint">Click a bubble to explore · bubble size = population · colour = selected metric</p>', unsafe_allow_html=True)

    # Handle click
    if clicked and clicked.get("selection") and clicked["selection"].get("points"):
        pt = clicked["selection"]["points"][0]
        curve = pt.get("curve_number", 0)
        if curve < len(df):
            lhin_name = plot_df.iloc[curve]["LHIN"]
            if lhin_name != st.session_state.selected_lhin:
                st.session_state.selected_lhin = lhin_name
                st.rerun()

with detail_col:
    sel = st.session_state.selected_lhin
    row = df[df["LHIN"] == sel].iloc[0] if sel else None

    if row is None:
        # Province-wide summary
        st.markdown('<p class="section-label">Province overview</p>', unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(2), st.columns(2), None, None
        cols = st.columns(2)
        with cols[0]:
            st.metric("Total population", f"{df['population'].sum()/1e6:.1f}M")
            st.metric("Avg GPs / 1,000", f"{df['gp_per_1000'].mean():.2f}")
        with cols[1]:
            st.metric("LHINs undersupplied", f"{(df['gap_score']>1.1).sum()} / 14")
            st.metric("Avg specialists / 1,000", f"{df['spec_per_1000'].mean():.2f}")

        st.markdown('<p class="section-label">Gap score by LHIN</p>', unsafe_allow_html=True)
        gap_sorted = df.sort_values("gap_score", ascending=True)
        fig_gap = go.Figure(go.Bar(
            x=gap_sorted["gap_score"],
            y=gap_sorted["LHIN"],
            orientation="h",
            marker_color=[
                "#3fb950" if g < 0.95 else ("#d29922" if g < 1.15 else "#f85149")
                for g in gap_sorted["gap_score"]
            ],
            hovertemplate="<b>%{y}</b><br>Gap score: %{x:.2f}<extra></extra>",
        ))
        fig_gap.add_vline(x=1.0, line_dash="dot", line_color="rgba(255,255,255,0.3)", line_width=1)
        fig_gap.update_layout(
            margin=dict(l=0,r=10,t=0,b=0), height=340,
            paper_bgcolor="#161b22", plot_bgcolor="#161b22",
            xaxis=dict(color="#7d8590", gridcolor="#21262d", title=""),
            yaxis=dict(color="#c9d1d9", gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10)),
            bargap=0.25,
        )
        st.plotly_chart(fig_gap, use_container_width=True)
        st.markdown('<p class="map-hint">← Click a bubble on the map to drill into any LHIN</p>', unsafe_allow_html=True)

    else:
        # LHIN detail view
        gap = row["gap_score"]
        gap_class = "gap-good" if gap < 0.95 else ("gap-med" if gap < 1.15 else "gap-bad")
        gap_text  = "Well served" if gap < 0.95 else ("Moderate gap" if gap < 1.15 else "Undersupplied")

        c1, c2 = st.columns([3,1])
        with c1:
            st.markdown(f"### {row['LHIN']}")
            st.markdown(f'<span class="gap-pill {gap_class}">{gap_text}</span>', unsafe_allow_html=True)
        with c2:
            if st.button("✕ Clear", type="secondary", use_container_width=True):
                st.session_state.selected_lhin = None
                st.rerun()

        # PHU list
        phus = PHU_MAP.get(row["LHIN"], [])
        st.caption(f"Public Health Units: {', '.join(phus)}")

        # Key metrics
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Population", f"{row['population']/1000:.0f}K")
        with m2:
            st.metric("65+ share", f"{row['pct_65plus']}%",
                      delta=f"{row['pct_65plus']-13.6:.1f}% vs ON avg",
                      delta_color="inverse")
        with m3:
            st.metric("Gap score", f"{gap:.2f}",
                      delta=f"{'↑ above' if gap>1 else '↓ below'} benchmark",
                      delta_color="inverse")

        # Age pyramid
        st.markdown('<p class="section-label">Population by age group</p>', unsafe_allow_html=True)
        age_vals = [row[f"pop_{ag}"] for ag in AGE_GROUPS]
        fig_age = go.Figure(go.Bar(
            x=age_vals, y=AGE_GROUPS, orientation="h",
            marker_color=AGE_COLORS,
            text=[f"{v/1000:.1f}K" for v in age_vals],
            textposition="outside",
            textfont=dict(size=10, color="#7d8590"),
            hovertemplate="<b>%{y}</b><br>%{x:,} people<extra></extra>",
        ))
        fig_age.update_layout(
            margin=dict(l=0,r=40,t=0,b=0), height=200,
            paper_bgcolor="#161b22", plot_bgcolor="#161b22",
            xaxis=dict(color="#7d8590", gridcolor="#21262d", showticklabels=False),
            yaxis=dict(color="#c9d1d9", gridcolor="rgba(0,0,0,0)"),
            bargap=0.2,
        )
        st.plotly_chart(fig_age, use_container_width=True)

        # Provider breakdown
        st.markdown('<p class="section-label">Provider supply vs. Ontario benchmark</p>', unsafe_allow_html=True)
        providers = [
            ("Family physicians (GPs)", row["gp_per_1000"],   BENCHMARK_GP,   row["gp_count"]),
            ("Specialists",             row["spec_per_1000"],  BENCHMARK_SPEC, row["spec_count"]),
            ("Nurse Practitioners",     row["np_per_1000"],    BENCHMARK_NP,   row["np_count"]),
        ]
        for name, rate, bench, count in providers:
            ratio = rate / bench
            bar_color = "#3fb950" if ratio >= 0.95 else ("#d29922" if ratio >= 0.75 else "#f85149")
            pct = min(ratio, 1.5) / 1.5 * 100
            bench_pct = (1.0/1.5)*100
            delta_txt = f"+{(ratio-1)*100:.0f}%" if ratio >= 1 else f"{(ratio-1)*100:.0f}%"
            delta_col = "#3fb950" if ratio >= 0.95 else ("#d29922" if ratio >= 0.75 else "#f85149")
            st.markdown(f"""
            <div class="provider-row">
              <div>
                <div class="provider-name">{name}</div>
                <div style="font-size:0.7rem;color:#7d8590;margin-top:2px">{count:,} total · {rate:.2f}/1,000</div>
              </div>
              <div style="display:flex;align-items:center;gap:10px">
                <div style="width:90px;height:6px;background:#21262d;border-radius:3px;position:relative">
                  <div style="width:{pct:.0f}%;height:6px;background:{bar_color};border-radius:3px"></div>
                  <div style="position:absolute;top:-8px;left:{bench_pct:.0f}%;width:1px;height:22px;background:rgba(255,255,255,0.3)"></div>
                </div>
                <span style="font-size:0.72rem;color:{delta_col};font-weight:600;min-width:34px">{delta_txt}</span>
              </div>
            </div>""", unsafe_allow_html=True)

        # Demand vs supply gauge
        st.markdown('<p class="section-label">Demand–supply balance</p>', unsafe_allow_html=True)
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=gap,
            delta=dict(reference=1.0, increasing=dict(color="#f85149"), decreasing=dict(color="#3fb950")),
            gauge=dict(
                axis=dict(range=[0.5, 1.6], tickcolor="#7d8590", tickfont=dict(color="#7d8590",size=9)),
                bar=dict(color=("#3fb950" if gap<0.95 else ("#d29922" if gap<1.15 else "#f85149")), thickness=0.35),
                bgcolor="#21262d",
                steps=[
                    dict(range=[0.5,0.95],  color="#0d3320"),
                    dict(range=[0.95,1.15], color="#3d2c00"),
                    dict(range=[1.15,1.6],  color="#3d0a08"),
                ],
                threshold=dict(line=dict(color="white",width=2), thickness=0.8, value=1.0),
            ),
            number=dict(font=dict(color="#e6edf3", size=28)),
        ))
        fig_g.update_layout(
            margin=dict(l=20,r=20,t=10,b=0), height=130,
            paper_bgcolor="#161b22",
            font=dict(color="#7d8590"),
        )
        st.plotly_chart(fig_g, use_container_width=True)
        st.caption("Gap score: demand index ÷ weighted supply index. >1.0 = undersupplied. Benchmark line at 1.0.")

# ──────────────────────────────────────────
# BOTTOM: PROVINCE COMPARISON TABLE
# ──────────────────────────────────────────
st.divider()
st.markdown('<p class="section-label">All LHINs — comparative summary</p>', unsafe_allow_html=True)

display_df = df[[
    "LHIN","type","population","pct_65plus",
    "gp_per_1000","spec_per_1000","np_per_1000","gap_score"
]].copy()
display_df.columns = ["LHIN","Type","Population","65+ %","GPs/1K","Specialists/1K","NPs/1K","Gap score"]
display_df["Population"] = display_df["Population"].apply(lambda x: f"{x:,}")
display_df["GPs/1K"]          = display_df["GPs/1K"].round(2)
display_df["Specialists/1K"]  = display_df["Specialists/1K"].round(2)
display_df["NPs/1K"]          = display_df["NPs/1K"].round(2)
display_df["Gap score"]       = display_df["Gap score"].round(2)
display_df["Type"] = display_df["Type"].str.title()

st.dataframe(
    display_df.sort_values("Gap score", ascending=False),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Gap score": st.column_config.ProgressColumn(
            "Gap score", min_value=0.5, max_value=1.6, format="%.2f"
        ),
        "65+ %": st.column_config.NumberColumn(format="%.1f%%"),
    }
)
