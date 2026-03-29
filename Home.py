from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st

st.set_page_config(
    page_title="CareGap",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
.main { background: #0d1117; }
.page-title { font-size: 1.4rem; font-weight: 600; color: #e6edf3; margin-bottom: 0; }
.page-sub { font-size: 0.78rem; color: #7d8590; margin-top: 2px; margin-bottom: 12px; }
.section-label { font-size: 0.68rem; font-weight: 600; color: #7d8590; text-transform: uppercase; letter-spacing: 0.09em; margin: 18px 0 8px; }
</style>
""",
    unsafe_allow_html=True,
)

ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "inputData"
PROCESSED_DIR = ROOT / "data" / "processed"
STATIC_DIR = ROOT / "data" / "static"

AGE_GROUP_UNDER18 = ["0–14", "15–24"]
AGE_GROUP_18_64 = ["15–24", "25–44", "45–64"]
AGE_GROUP_65PLUS = ["65–74", "75–84", "85+"]

CONDITION_AGE_PROFILES = {
    "Pneumonia": {"u18": 0.05, "a18_64": 0.25, "a65p": 0.70},
    "Mental Health": {"u18": 0.10, "a18_64": 0.78, "a65p": 0.12},
    "Chronic Kidney Disease": {"u18": 0.02, "a18_64": 0.48, "a65p": 0.50},
    "Heart Failure": {"u18": 0.01, "a18_64": 0.24, "a65p": 0.75},
    "COPD": {"u18": 0.01, "a18_64": 0.34, "a65p": 0.65},
    "Type 2 Diabetes": {"u18": 0.01, "a18_64": 0.59, "a65p": 0.40},
    "Hypertension": {"u18": 0.01, "a18_64": 0.64, "a65p": 0.35},
    "Stroke": {"u18": 0.01, "a18_64": 0.19, "a65p": 0.80},
    # Not in the current CSV, but included for extensibility.
    "Dementia": {"u18": 0.01, "a18_64": 0.09, "a65p": 0.90},
}


@st.cache_data
def load_all_data() -> dict[str, pd.DataFrame]:
    return {
        "layer1": pd.read_csv(INPUT_DIR / "layer1_population_demographics.csv"),
        "layer2": pd.read_csv(INPUT_DIR / "layer2_current_burden.csv"),
        "layer3": pd.read_csv(INPUT_DIR / "layer3_predictive_trajectory.csv"),
        "layer4": pd.read_csv(INPUT_DIR / "layer4_cost_analysis.csv"),
        "pop_age_lhin": pd.read_csv(PROCESSED_DIR / "population_by_age_lhin.csv"),
        "pop_proj": pd.read_csv(PROCESSED_DIR / "population_projections.csv"),
        "lhin_coords": pd.read_csv(STATIC_DIR / "lhin_coords.csv"),
        "providers": pd.read_csv(INPUT_DIR / "processed data" / "providers_by_lhin.csv"),
    }


def _to_fraction(v: float) -> float:
    v = float(v) if pd.notna(v) else 0.0
    return v / 100.0 if v > 1 else v


def _safe_choice(row: pd.DataFrame, col: str, fallback: float) -> float:
    if row.empty or col not in row.columns:
        return fallback
    val = row.iloc[0][col]
    return float(val) if pd.notna(val) else fallback


def _quantile_band(series: pd.Series, labels: list[str]) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").fillna(0)
    if s.nunique() <= 1:
        return pd.Series([labels[1]] * len(s), index=s.index)
    q1, q2 = s.quantile([0.33, 0.66]).tolist()
    return pd.cut(
        s,
        bins=[-float("inf"), q1, q2, float("inf")],
        labels=labels,
        include_lowest=True,
    ).astype(str)


def _size_scale(series: pd.Series, lo: float = 20000, hi: float = 220000) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").fillna(0)
    if s.nunique() <= 1:
        return pd.Series([70000.0] * len(s), index=s.index)
    s_min, s_max = float(s.min()), float(s.max())
    return lo + (s - s_min) * (hi - lo) / (s_max - s_min)


def _metric_band(series: pd.Series) -> pd.Series:
    return _quantile_band(series, ["Low", "Moderate", "High"])


def _band_with_breaks(series: pd.Series) -> tuple[pd.Series, float, float]:
    s = pd.to_numeric(series, errors="coerce").fillna(0)
    if s.nunique() <= 1:
        return pd.Series(["Moderate"] * len(s), index=s.index), float(s.iloc[0]), float(s.iloc[0])
    q1, q2 = s.quantile([0.33, 0.66]).tolist()
    band = pd.cut(
        s,
        bins=[-float("inf"), q1, q2, float("inf")],
        labels=["Low", "Moderate", "High"],
        include_lowest=True,
    ).astype(str)
    return band, float(q1), float(q2)


def _proportional_radius(series: pd.Series, bubble_scale: float, zoom: float) -> pd.Series:
    # Area-proportional bubbles: radius follows sqrt(value).
    s = pd.to_numeric(series, errors="coerce").fillna(0)
    s = s.clip(lower=0)
    if s.nunique() <= 1:
        return pd.Series([16.0 * bubble_scale] * len(s), index=s.index)

    s_norm = s / s.max()
    radius = np.sqrt(s_norm)

    # Adapt max bubble size to map zoom so bubbles remain readable across map scales.
    max_px = np.interp(float(zoom), [4.2, 6.2], [58.0, 34.0])
    min_px = np.interp(float(zoom), [4.2, 6.2], [8.0, 5.0])
    return (min_px + radius * (max_px - min_px)) * bubble_scale


def _ontario_view_state(df: pd.DataFrame) -> pdk.ViewState:
    lat = pd.to_numeric(df["lat"], errors="coerce")
    lon = pd.to_numeric(df["lon"], errors="coerce")
    lat_min, lat_max = float(lat.min()), float(lat.max())
    lon_min, lon_max = float(lon.min()), float(lon.max())
    lat_span = max(lat_max - lat_min, 0.1)
    lon_span = max(lon_max - lon_min, 0.1)
    span = max(lat_span, lon_span)

    if span > 9:
        zoom = 4.4
    elif span > 6:
        zoom = 4.8
    elif span > 4:
        zoom = 5.2
    else:
        zoom = 5.8

    return pdk.ViewState(
        latitude=float((lat_min + lat_max) / 2),
        longitude=float((lon_min + lon_max) / 2),
        zoom=zoom,
        pitch=0,
    )


def build_statscan_projection_to_2050(pop_proj: pd.DataFrame, end_year: int = 2050) -> pd.DataFrame:
    proj = pop_proj.copy()
    proj["year"] = pd.to_numeric(proj["year"], errors="coerce")

    out = []
    for (scenario, age_group), g in proj.groupby(["scenario_label", "age_group"]):
        g = g.sort_values("year")
        years = g["year"].astype(int).tolist()
        vals = g["population"].astype(float).tolist()

        min_y = int(min(years))
        target_years = list(range(min_y, end_year + 1))

        value_by_year = {y: v for y, v in zip(years, vals)}

        def _cagr(y0: int, v0: float, y1: int, v1: float) -> float:
            if y1 <= y0 or v0 <= 0 or v1 <= 0:
                return 0.0
            return (v1 / v0) ** (1.0 / (y1 - y0)) - 1.0

        for y in target_years:
            if y in value_by_year:
                val = value_by_year[y]
            else:
                lower = [yy for yy in years if yy < y]
                upper = [yy for yy in years if yy > y]
                if lower and upper:
                    y0, y1 = max(lower), min(upper)
                    v0, v1 = value_by_year[y0], value_by_year[y1]
                    r = _cagr(y0, v0, y1, v1)
                    val = v0 * ((1 + r) ** (y - y0))
                elif lower:
                    y0 = max(lower)
                    v0 = value_by_year[y0]
                    if len(years) >= 2:
                        y_prev = years[-2]
                        v_prev = value_by_year[y_prev]
                        r = _cagr(y_prev, v_prev, years[-1], value_by_year[years[-1]])
                    else:
                        r = 0.0
                    val = v0 * ((1 + r) ** (y - y0))
                else:
                    val = value_by_year[min(years)]

            out.append(
                {
                    "year": int(y),
                    "scenario": scenario,
                    "scenario_label": scenario,
                    "age_group": age_group,
                    "population": float(val),
                }
            )

    return pd.DataFrame(out)


def build_lhin_projection(
    data: dict[str, pd.DataFrame],
    pop_proj_ext: pd.DataFrame,
    condition: str,
    year: int,
    scenario: str,
) -> pd.DataFrame:
    layer2 = data["layer2"].copy()
    layer3 = data["layer3"].copy()
    layer4 = data["layer4"].copy()
    pop_age = data["pop_age_lhin"].copy()
    pop_proj = pop_proj_ext.copy()
    coords = data["lhin_coords"].copy()
    providers = data["providers"].copy()

    for frame in [layer2, layer3, pop_age, pop_proj]:
        frame["year"] = pd.to_numeric(frame["year"], errors="coerce")

    base_year = int(pop_age["year"].min())
    base_pop = pop_age[pop_age["year"] == base_year].copy()

    if "lat" not in base_pop.columns or "lon" not in base_pop.columns:
        base_pop = base_pop.merge(coords, left_on="LHIN", right_on="lhin_name", how="left")

    proj_use = pop_proj[pop_proj["scenario_label"] == scenario].copy()
    if proj_use.empty:
        proj_use = pop_proj[pop_proj["scenario_label"] == "Reference"].copy()

    base_proj = proj_use[proj_use["year"] == proj_use["year"].min()][["age_group", "population"]].rename(
        columns={"population": "base_pop"}
    )
    target_proj = proj_use[proj_use["year"] == year][["age_group", "population"]].rename(
        columns={"population": "target_pop"}
    )
    if target_proj.empty:
        target_proj = base_proj.rename(columns={"base_pop": "target_pop"})

    growth = base_proj.merge(target_proj, on="age_group", how="left")
    growth["target_pop"] = growth["target_pop"].fillna(growth["base_pop"])
    growth["age_multiplier"] = growth["target_pop"] / growth["base_pop"].replace(0, np.nan)
    growth["age_multiplier"] = growth["age_multiplier"].fillna(1.0)

    projected_age = base_pop.merge(growth[["age_group", "age_multiplier"]], on="age_group", how="left")
    projected_age["age_multiplier"] = projected_age["age_multiplier"].fillna(1.0)
    projected_age["projected_population"] = projected_age["population"] * projected_age["age_multiplier"]

    under18 = projected_age[projected_age["age_group"].isin(AGE_GROUP_UNDER18)].groupby("LHIN", as_index=False)[
        "projected_population"
    ].sum().rename(columns={"projected_population": "pop_under18"})
    age18_64 = projected_age[projected_age["age_group"].isin(AGE_GROUP_18_64)].groupby("LHIN", as_index=False)[
        "projected_population"
    ].sum().rename(columns={"projected_population": "pop_18_64"})
    age65p = projected_age[projected_age["age_group"].isin(AGE_GROUP_65PLUS)].groupby("LHIN", as_index=False)[
        "projected_population"
    ].sum().rename(columns={"projected_population": "pop_65_plus"})
    pop_total = projected_age.groupby("LHIN", as_index=False)["projected_population"].sum().rename(
        columns={"projected_population": "pop_total"}
    )
    pop_base_total = base_pop.groupby("LHIN", as_index=False)["population"].sum().rename(
        columns={"population": "pop_base_total"}
    )
    lhin_geo = projected_age.groupby("LHIN", as_index=False).agg({"lat": "first", "lon": "first"})

    lhin = pop_total.merge(pop_base_total, on="LHIN", how="left").merge(under18, on="LHIN", how="left").merge(age18_64, on="LHIN", how="left").merge(
        age65p, on="LHIN", how="left"
    ).merge(lhin_geo, on="LHIN", how="left")

    provider_totals = (
        providers.groupby("lhin", as_index=False)["physicians_count"].sum()
        .rename(columns={"lhin": "LHIN", "physicians_count": "physicians_total"})
    )
    family = (
        providers[providers["specialty"].str.contains("family", case=False, na=False)]
        .groupby("lhin", as_index=False)["physicians_count"]
        .sum()
        .rename(columns={"lhin": "LHIN", "physicians_count": "family_physicians"})
    )
    lhin = lhin.merge(provider_totals, on="LHIN", how="left").merge(family, on="LHIN", how="left")
    lhin[["physicians_total", "family_physicians"]] = lhin[["physicians_total", "family_physicians"]].fillna(0)

    c2 = layer2[layer2["condition"] == condition]
    c3_condition = layer3[layer3["condition"] == condition].copy()
    c3_scenario = c3_condition[c3_condition["scenario"] == scenario].copy()
    if c3_scenario.empty:
        c3_scenario = c3_condition.copy()
    c4 = layer4[layer4["condition"] == condition]

    profile = CONDITION_AGE_PROFILES.get(condition)
    if profile is None:
        w_u18 = _to_fraction(_safe_choice(c2, "pct_ed_visits_under_18", 0.15))
        w_18_64 = _to_fraction(_safe_choice(c2, "pct_ed_visits_18_64", 0.65))
        w_65p = _to_fraction(_safe_choice(c2, "pct_ed_visits_65plus", 0.20))
    else:
        w_u18 = profile["u18"]
        w_18_64 = profile["a18_64"]
        w_65p = profile["a65p"]

    lhin["demand_score"] = (lhin["pop_under18"] * w_u18) + (lhin["pop_18_64"] * w_18_64) + (lhin["pop_65_plus"] * w_65p)
    lhin["weight"] = lhin["demand_score"] / lhin["demand_score"].sum()
    lhin["weight"] = lhin["weight"].fillna(0)
    if lhin["weight"].sum() > 0:
        lhin["weight"] = lhin["weight"] / lhin["weight"].sum()

    base_year_condition = int(_safe_choice(c2, "year", 2024))
    base_admissions = _safe_choice(c2, "admissions", 0.0)
    base_ed = _safe_choice(c2, "ed_visits", 0.0)
    base_avoidable = _safe_choice(c2, "avoidable_admissions", 0.0)

    # Condition trend from layer3 growth assumptions; fall back to 0% if missing.
    growth_rate_pct = _safe_choice(c3_scenario[c3_scenario["year"] == base_year_condition], "growth_rate_pct", np.nan)
    if np.isnan(growth_rate_pct):
        growth_rate_pct = _safe_choice(c3_scenario, "growth_rate_pct", 0.0)

    years_out = year - base_year_condition
    trend_multiplier = (1 + (growth_rate_pct / 100.0)) ** years_out

    # Age pressure multiplier from StatsCan population projections.
    base_age = proj_use[proj_use["year"] == proj_use["year"].min()][["age_group", "population"]].rename(
        columns={"population": "base_pop_scn"}
    )
    target_age = proj_use[proj_use["year"] == year][["age_group", "population"]].rename(
        columns={"population": "target_pop_scn"}
    )
    if target_age.empty:
        target_age = base_age.rename(columns={"base_pop_scn": "target_pop_scn"})

    age_pressure = base_age.merge(target_age, on="age_group", how="left")
    age_pressure["target_pop_scn"] = age_pressure["target_pop_scn"].fillna(age_pressure["base_pop_scn"])
    age_pressure["ratio"] = age_pressure["target_pop_scn"] / age_pressure["base_pop_scn"].replace(0, np.nan)
    age_pressure["ratio"] = age_pressure["ratio"].fillna(1.0)

    def _weighted_ratio(groups: list[str], fallback: float = 1.0) -> float:
        vals = age_pressure[age_pressure["age_group"].isin(groups)]["ratio"]
        return float(vals.mean()) if not vals.empty else fallback

    age_multiplier = (
        (w_u18 * _weighted_ratio(AGE_GROUP_UNDER18))
        + (w_18_64 * _weighted_ratio(AGE_GROUP_18_64))
        + (w_65p * _weighted_ratio(AGE_GROUP_65PLUS))
    )

    condition_multiplier = trend_multiplier * age_multiplier

    provincial_admissions = base_admissions * condition_multiplier
    provincial_ed = base_ed * condition_multiplier
    provincial_avoidable_adm = base_avoidable * condition_multiplier
    avg_cost = _safe_choice(c4, "avg_cost_per_admission", _safe_choice(c2, "avg_cost_per_admission", 0.0))
    provincial_capacity = _safe_choice(c2, "effective_physician_capacity_fte", 0.0)

    lhin["predicted_admissions"] = lhin["weight"] * provincial_admissions
    lhin["predicted_ed_visits"] = lhin["weight"] * provincial_ed
    lhin["predicted_avoidable_admissions"] = lhin["weight"] * provincial_avoidable_adm
    lhin["predicted_cost"] = lhin["predicted_admissions"] * avg_cost

    provider_share = lhin["physicians_total"] / lhin["physicians_total"].replace(0, np.nan).sum()
    provider_share = provider_share.fillna(0)
    lhin["allocated_capacity_fte"] = provider_share * provincial_capacity

    lhin["admissions_per_100k"] = lhin["predicted_admissions"] / lhin["pop_total"].replace(0, np.nan) * 100000
    lhin["admissions_per_100k"] = lhin["admissions_per_100k"].fillna(0)
    admissions_per_fte = provincial_admissions / provincial_capacity if provincial_capacity > 0 else 0
    lhin["expected_capacity_admissions"] = lhin["allocated_capacity_fte"] * admissions_per_fte
    lhin["capacity_strain"] = lhin["predicted_admissions"] / lhin["expected_capacity_admissions"].replace(0, np.nan)
    lhin["capacity_strain"] = lhin["capacity_strain"].fillna(0)
    lhin["cost_m"] = lhin["predicted_cost"] / 1_000_000
    lhin["physicians_per_100k"] = lhin["physicians_total"] / lhin["pop_total"].replace(0, np.nan) * 100000
    lhin["physicians_per_100k"] = lhin["physicians_per_100k"].fillna(0)
    lhin["senior_share_pct"] = lhin["pop_65_plus"] / lhin["pop_total"].replace(0, np.nan) * 100
    lhin["senior_share_pct"] = lhin["senior_share_pct"].fillna(0)
    lhin["population_delta"] = lhin["pop_total"] - lhin["pop_base_total"]
    lhin["population_growth_pct"] = lhin["population_delta"] / lhin["pop_base_total"].replace(0, np.nan) * 100
    lhin["population_growth_pct"] = lhin["population_growth_pct"].fillna(0)

    # Add Ontario total aggregate as the default high-level view.
    ont = {
        "LHIN": "Ontario Total",
        "pop_total": lhin["pop_total"].sum(),
        "pop_base_total": lhin["pop_base_total"].sum(),
        "pop_under18": lhin["pop_under18"].sum(),
        "pop_18_64": lhin["pop_18_64"].sum(),
        "pop_65_plus": lhin["pop_65_plus"].sum(),
        "lat": lhin["lat"].mean(),
        "lon": lhin["lon"].mean(),
        "physicians_total": lhin["physicians_total"].sum(),
        "family_physicians": lhin["family_physicians"].sum(),
        "demand_score": lhin["demand_score"].sum(),
        "weight": 1.0,
        "predicted_admissions": lhin["predicted_admissions"].sum(),
        "predicted_ed_visits": lhin["predicted_ed_visits"].sum(),
        "predicted_avoidable_admissions": lhin["predicted_avoidable_admissions"].sum(),
        "predicted_cost": lhin["predicted_cost"].sum(),
        "allocated_capacity_fte": lhin["allocated_capacity_fte"].sum(),
        "expected_capacity_admissions": lhin["expected_capacity_admissions"].sum(),
        "admissions_per_100k": 0.0,
        "capacity_strain": 0.0,
        "cost_m": lhin["cost_m"].sum(),
        "physicians_per_100k": 0.0,
        "senior_share_pct": 0.0,
        "population_delta": lhin["population_delta"].sum(),
        "population_growth_pct": 0.0,
    }
    if ont["pop_total"] > 0:
        ont["admissions_per_100k"] = ont["predicted_admissions"] / ont["pop_total"] * 100000
        ont["physicians_per_100k"] = ont["physicians_total"] / ont["pop_total"] * 100000
        ont["senior_share_pct"] = ont["pop_65_plus"] / ont["pop_total"] * 100
    if ont["expected_capacity_admissions"] > 0:
        ont["capacity_strain"] = ont["predicted_admissions"] / ont["expected_capacity_admissions"]
    if ont["pop_base_total"] > 0:
        ont["population_growth_pct"] = ont["population_delta"] / ont["pop_base_total"] * 100

    lhin = pd.concat([lhin, pd.DataFrame([ont])], ignore_index=True)

    return lhin


def build_trajectory(
    data: dict[str, pd.DataFrame],
    pop_proj_ext: pd.DataFrame,
    condition: str,
    scenarios: list[str],
    end_year: int = 2050,
) -> pd.DataFrame:
    layer3 = data["layer3"].copy()
    layer2 = data["layer2"].copy()
    pop_proj = pop_proj_ext.copy()
    layer3["year"] = pd.to_numeric(layer3["year"], errors="coerce")
    layer2["year"] = pd.to_numeric(layer2["year"], errors="coerce")
    pop_proj["year"] = pd.to_numeric(pop_proj["year"], errors="coerce")

    c2 = layer2[layer2["condition"] == condition]
    if c2.empty:
        return pd.DataFrame()

    base_year = int(_safe_choice(c2, "year", 2024))
    base_adm = _safe_choice(c2, "admissions", 0.0)
    base_ed = _safe_choice(c2, "ed_visits", 0.0)
    base_avoid = _safe_choice(c2, "avoidable_admissions", 0.0)

    prof = CONDITION_AGE_PROFILES.get(condition)
    if prof is None:
        w_u18 = _to_fraction(_safe_choice(c2, "pct_ed_visits_under_18", 0.15))
        w_18_64 = _to_fraction(_safe_choice(c2, "pct_ed_visits_18_64", 0.65))
        w_65p = _to_fraction(_safe_choice(c2, "pct_ed_visits_65plus", 0.20))
    else:
        w_u18 = prof["u18"]
        w_18_64 = prof["a18_64"]
        w_65p = prof["a65p"]

    years = list(range(base_year, end_year + 1))
    rows = []

    for scn in scenarios:
        c3 = layer3[(layer3["condition"] == condition) & (layer3["scenario"] == scn)]
        if c3.empty:
            c3 = layer3[(layer3["condition"] == condition) & (layer3["scenario"] == "Reference")]
        growth_rate_pct = _safe_choice(c3, "growth_rate_pct", 0.0)

        pop_scn = pop_proj[pop_proj["scenario_label"] == scn].copy()
        if pop_scn.empty:
            pop_scn = pop_proj[pop_proj["scenario_label"] == "Reference"].copy()
        if pop_scn.empty:
            continue

        for y in years:
            base_age = pop_scn[pop_scn["year"] == base_year][["age_group", "population"]].rename(
                columns={"population": "base_pop"}
            )
            y_age = pop_scn[pop_scn["year"] == y][["age_group", "population"]].rename(
                columns={"population": "target_pop"}
            )
            if y_age.empty or base_age.empty:
                continue

            merged = base_age.merge(y_age, on="age_group", how="left")
            merged["target_pop"] = merged["target_pop"].fillna(merged["base_pop"])
            merged["ratio"] = merged["target_pop"] / merged["base_pop"].replace(0, np.nan)
            merged["ratio"] = merged["ratio"].fillna(1.0)

            def _ratio(groups: list[str]) -> float:
                vals = merged[merged["age_group"].isin(groups)]["ratio"]
                return float(vals.mean()) if not vals.empty else 1.0

            age_mult = (w_u18 * _ratio(AGE_GROUP_UNDER18)) + (w_18_64 * _ratio(AGE_GROUP_18_64)) + (w_65p * _ratio(AGE_GROUP_65PLUS))
            trend_mult = (1 + (growth_rate_pct / 100.0)) ** (y - base_year)
            total_mult = age_mult * trend_mult

            total_pop = float(y_age["target_pop"].sum())
            senior_pop = float(y_age[y_age["age_group"].isin(AGE_GROUP_65PLUS)]["target_pop"].sum())

            rows.append(
                {
                    "condition": condition,
                    "year": y,
                    "scenario": scn,
                    "growth_rate_pct": growth_rate_pct,
                    "total_population": total_pop,
                    "senior_population": senior_pop,
                    "admissions": base_adm * total_mult,
                    "ed_visits": base_ed * total_mult,
                    "avoidable_admissions": base_avoid * total_mult,
                }
            )

    return pd.DataFrame(rows)


data = load_all_data()
pop_proj_ext = build_statscan_projection_to_2050(data["pop_proj"], end_year=2050)
conditions = sorted(data["layer2"]["condition"].dropna().unique().tolist())
year_options = sorted({int(y) for y in pop_proj_ext["year"].dropna().unique().tolist()})
scenario_options = sorted(pop_proj_ext["scenario_label"].dropna().unique().tolist())
trajectory_scenario_options = sorted(data["layer3"]["scenario"].dropna().unique().tolist())

with st.sidebar:
    st.markdown("### Forecast Controls")
    condition = st.selectbox("Condition", conditions)
    target_year = st.select_slider("Population Projection Year (StatsCan)", options=year_options, value=year_options[min(1, len(year_options) - 1)])
    scenario = st.selectbox("Scenario", scenario_options, index=scenario_options.index("Reference") if "Reference" in scenario_options else 0)
    trajectory_scenarios = st.multiselect("Trajectory Scenarios", trajectory_scenario_options, default=["Reference"] if "Reference" in trajectory_scenario_options else [trajectory_scenario_options[0]])

    st.divider()
    st.markdown("### Map Indicators")
    toggles = {
        "Admissions": st.toggle("Admissions", value=True),
        "Cost": st.toggle("Cost", value=True),
        "Capacity Strain": st.toggle("Capacity Strain", value=True),
        "Population Trajectory": st.toggle("Population Trajectory", value=True),
    }

    st.divider()
    st.markdown("### Visual Encoding")
    size_metric = st.selectbox(
        "Size by",
        options=["predicted_admissions", "predicted_ed_visits", "pop_total", "population_delta", "population_growth_pct", "physicians_total"],
        format_func=lambda x: {
            "predicted_admissions": "Admissions",
            "predicted_ed_visits": "ED Visits",
            "pop_total": "Population",
            "population_delta": "Population Increase",
            "population_growth_pct": "Population Growth %",
            "physicians_total": "Physician Supply",
        }[x],
    )
    color_metric = st.selectbox(
        "Color by",
        options=["capacity_strain", "admissions_per_100k", "cost_m", "physicians_per_100k", "senior_share_pct", "population_growth_pct"],
        format_func=lambda x: {
            "capacity_strain": "Capacity Strain",
            "admissions_per_100k": "Admissions per 100k",
            "cost_m": "Cost (M)",
            "physicians_per_100k": "Physicians per 100k",
            "senior_share_pct": "Senior Share %",
            "population_growth_pct": "Population Growth %",
        }[x],
    )
    shape_metric = st.selectbox(
        "Shape by",
        options=["capacity_strain", "senior_share_pct", "physicians_per_100k", "population_growth_pct"],
        format_func=lambda x: {
            "capacity_strain": "Capacity Strain Band",
            "senior_share_pct": "Senior Share Band",
            "physicians_per_100k": "Physician Density Band",
            "population_growth_pct": "Population Growth Band",
        }[x],
    )
    bubble_scale = st.slider("Bubble size", min_value=0.5, max_value=3.0, value=1.6, step=0.1)
    size_with_growth = st.toggle("Size bubbles by population increase", value=True)

lhin_df = build_lhin_projection(data, pop_proj_ext, condition, int(target_year), scenario)

st.markdown('<div class="page-title">CareGap</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="page-sub">Condition: <b>{condition}</b> | Scenario: <b>{scenario}</b> | Year: <b>{target_year}</b> (Ontario regional care gap model)</div>',
    unsafe_allow_html=True,
)

if lhin_df.empty:
    st.warning("No LHIN points available for this selection.")
else:
    active = [k for k, v in toggles.items() if v and k != "Population Trajectory"]
    if not active:
        active = ["Admissions"]

    size_source = size_metric if ("Admissions" in active or "Cost" in active or "Capacity Strain" in active) else "pop_total"
    color_source = color_metric
    shape_source = shape_metric

    view_state = _ontario_view_state(lhin_df)
    base_radius = _proportional_radius(lhin_df[size_source], bubble_scale, view_state.zoom)
    if size_with_growth:
        growth = pd.to_numeric(lhin_df["population_growth_pct"], errors="coerce").fillna(0).clip(lower=0)
        if growth.nunique() > 1:
            growth_boost = 0.75 + ((growth - growth.min()) / (growth.max() - growth.min())) * 0.75
        else:
            growth_boost = pd.Series([1.0] * len(growth), index=growth.index)
        lhin_df["map_radius"] = base_radius * growth_boost
    else:
        lhin_df["map_radius"] = base_radius

    lhin_df["color_band"], color_q1, color_q2 = _band_with_breaks(lhin_df[color_source])
    lhin_df["shape_band"], _, _ = _band_with_breaks(lhin_df[shape_source])
    color_lookup = {
        "Low": [253, 216, 53, 195],
        "Moderate": [171, 71, 188, 190],
        "High": [106, 27, 154, 185],
    }
    lhin_df["fill_color"] = lhin_df["color_band"].map(color_lookup)
    lhin_df["glyph"] = lhin_df["shape_band"].map({"Low": "●", "Moderate": "■", "High": "▲"}).fillna("●")

    col_map, col_detail = st.columns([2, 1], gap="medium")
    with col_map:
        map_data = lhin_df[[
            "LHIN", "lat", "lon", "map_radius", "fill_color", "glyph",
            "predicted_admissions", "predicted_ed_visits", "predicted_avoidable_admissions",
            "cost_m", "admissions_per_100k", "capacity_strain", "pop_total", "physicians_per_100k", "senior_share_pct",
            "population_delta", "population_growth_pct",
        ]].copy()

        # Keep all map-displayed numeric values to one decimal for consistency.
        map_display_cols = [
            "predicted_admissions",
            "predicted_ed_visits",
            "predicted_avoidable_admissions",
            "cost_m",
            "admissions_per_100k",
            "capacity_strain",
            "pop_total",
            "physicians_per_100k",
            "senior_share_pct",
            "population_delta",
            "population_growth_pct",
        ]
        for c in map_display_cols:
            map_data[c] = pd.to_numeric(map_data[c], errors="coerce").round(1)

        scatter = pdk.Layer(
            "ScatterplotLayer",
            data=map_data,
            get_position="[lon, lat]",
            get_radius="map_radius",
            radius_units="pixels",
            get_fill_color="fill_color",
            get_line_color=[225, 225, 225],
            line_width_min_pixels=1,
            radius_scale=1,
            pickable=True,
            stroked=True,
        )
        labels = pdk.Layer(
            "TextLayer",
            data=map_data,
            get_position="[lon, lat]",
            get_text="glyph",
            get_size=16,
            get_color=[240, 240, 240, 220],
            get_alignment_baseline="center",
            get_text_anchor="middle",
            pickable=False,
        )

        deck = pdk.Deck(
            map_provider="carto",
            map_style="light",
            initial_view_state=view_state,
            layers=[scatter, labels],
            tooltip={
                "html": "<b>{LHIN}</b><br/>Admissions: {predicted_admissions}<br/>ED visits: {predicted_ed_visits}<br/>Avoidable admissions: {predicted_avoidable_admissions}<br/>Cost (M): {cost_m}<br/>Admissions/100k: {admissions_per_100k}<br/>Capacity strain: {capacity_strain}<br/>Physicians/100k: {physicians_per_100k}<br/>Senior share %: {senior_share_pct}<br/>Population: {pop_total}<br/>Population increase: {population_delta}<br/>Population growth %: {population_growth_pct}",
                "style": {"backgroundColor": "#0d1117", "color": "#e6edf3"},
            },
        )
        st.markdown("#### Ontario Regional Burden Map")
        map_col, legend_col = st.columns([20, 2], gap="small")
        with map_col:
            st.pydeck_chart(deck, width="stretch")

        with legend_col:
            st.markdown(
                f"""
                <div style="height:100%; min-height:520px; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#e6edf3; font-size:0.78rem;">
                  <div style="font-weight:600; text-align:center; margin-bottom:10px; line-height:1.2;">{color_source.replace('_', ' ').title()}</div>
                  <div style="display:flex; flex-direction:column; align-items:center; gap:8px;">
                    <div style="font-size:0.72rem; color:#b8c1cc; text-align:center;">High &gt; {color_q2:,.1f}</div>
                    <div style="width:22px; height:340px; border-radius:12px; border:1px solid #2f3742; background: linear-gradient(to top, #fdd835 0%, #ab47bc 55%, #6a1b9a 100%);"></div>
                    <div style="font-size:0.72rem; color:#b8c1cc; text-align:center;">Low ≤ {color_q1:,.1f}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_detail:
        lhin_options = sorted(lhin_df["LHIN"].unique().tolist())
        default_idx = lhin_options.index("Ontario Total") if "Ontario Total" in lhin_options else 0
        selected = st.selectbox("LHIN Focus (Local Health Integration Network)", lhin_options, index=default_idx)
        row = lhin_df[lhin_df["LHIN"] == selected].iloc[0]

        st.markdown(f"## {selected}")
        st.markdown('<p class="section-label">Condition Burden</p>', unsafe_allow_html=True)
        if toggles["Admissions"]:
            st.metric("Admissions", f"{row['predicted_admissions']:,.0f}")
        if toggles["Cost"]:
            st.metric("Estimated Cost", f"${row['cost_m']:.2f}M")
        if toggles["Capacity Strain"]:
            st.metric("Capacity Strain", f"{row['capacity_strain']:.2f}")

        st.markdown('<p class="section-label">Top Impact LHINs</p>', unsafe_allow_html=True)
        st.dataframe(
            lhin_df[["LHIN", "predicted_admissions", "cost_m", "capacity_strain"]]
            .sort_values("predicted_admissions", ascending=False)
            .head(5)
            .rename(columns={
                "predicted_admissions": "Admissions",
                "cost_m": "Cost (M)",
                "capacity_strain": "Capacity Strain",
            }),
            hide_index=True,
            width="stretch",
        )

st.divider()
if toggles["Population Trajectory"]:
    t = build_trajectory(data, pop_proj_ext, condition, trajectory_scenarios or [scenario], end_year=2050)
    st.markdown('<p class="section-label">Population and Burden Trajectory</p>', unsafe_allow_html=True)
    if t.empty:
        st.info("No trajectory rows found for this condition/scenario selection.")
    else:
        indicators = st.multiselect(
            "Toggle trajectory indicators",
            options=["total_population", "senior_population", "ed_visits", "avoidable_admissions"],
            default=["total_population", "senior_population", "ed_visits"],
        )
        long_df = t.melt(
            id_vars=["year", "scenario"],
            value_vars=indicators,
            var_name="indicator",
            value_name="value",
        )
        long_df["series"] = long_df["scenario"] + " • " + long_df["indicator"]
        fig_t = px.line(long_df, x="year", y="value", color="series", markers=True)
        y_max = float(pd.to_numeric(long_df["value"], errors="coerce").max())
        fig_t.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0d1117",
            plot_bgcolor="#0d1117",
            margin={"l": 12, "r": 10, "t": 10, "b": 72},
            height=520,
            xaxis_title="Year",
            yaxis_title="Value",
            legend_title_text="Scenario • Indicator",
        )
        fig_t.update_yaxes(
            automargin=True,
            tickformat=",.1f",
            ticklabelposition="outside",
            ticksuffix=" ",
            rangemode="tozero",
        )
        if y_max >= 1_000_000:
            fig_t.update_yaxes(tickmode="linear", tick0=0, dtick=1_000_000)
        fig_t.update_xaxes(automargin=True, ticklabelposition="outside")
        st.plotly_chart(fig_t, width="stretch")

st.caption("Integrated from layer1 population baseline, layer2 burden, layer3 trajectory, layer4 cost model, and LHIN age-population projections.")
