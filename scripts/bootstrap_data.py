from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "inputData"
INPUT_PROCESSED = INPUT_DIR / "processed data"
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
STATIC_DIR = DATA_DIR / "static"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


AGE_SHARES = {
    "0–14": 0.16,
    "15–24": 0.12,
    "25–44": 0.26,
    "45–64": 0.26,
    "65–74": 0.11,
    "75–84": 0.06,
    "85+": 0.03,
}


def build_population_by_age_lhin() -> pd.DataFrame:
    providers_path = INPUT_PROCESSED / "providers_by_lhin.csv"
    coords_path = STATIC_DIR / "lhin_coords.csv"

    providers = pd.read_csv(providers_path)
    coords = pd.read_csv(coords_path)

    # One population value per LHIN.
    lhin_pop = (
        providers[["lhin", "population"]]
        .dropna()
        .drop_duplicates(subset=["lhin"])
        .rename(columns={"lhin": "LHIN"})
    )

    records = []
    for _, row in lhin_pop.iterrows():
        for age_group, share in AGE_SHARES.items():
            records.append(
                {
                    "LHIN": row["LHIN"],
                    "year": 2024,
                    "age_group": age_group,
                    "population": int(round(float(row["population"]) * share)),
                }
            )

    out = pd.DataFrame(records)
    out = out.merge(coords, left_on="LHIN", right_on="lhin_name", how="left")
    out.to_csv(PROCESSED_DIR / "population_by_age_lhin.csv", index=False)
    return out


def build_population_projections(base_df: pd.DataFrame) -> pd.DataFrame:
    multipliers = {
        "Low": {2024: 1.00, 2029: 1.03, 2034: 1.07},
        "Reference": {2024: 1.00, 2029: 1.06, 2034: 1.12},
        "High": {2024: 1.00, 2029: 1.09, 2034: 1.18},
    }

    baseline = base_df.groupby("age_group", as_index=False)["population"].sum()

    rows = []
    for scenario, years in multipliers.items():
        for year, m in years.items():
            for _, rec in baseline.iterrows():
                rows.append(
                    {
                        "year": year,
                        "scenario": scenario,
                        "scenario_label": scenario,
                        "age_group": rec["age_group"],
                        "population": int(round(float(rec["population"]) * m)),
                    }
                )

    out = pd.DataFrame(rows)
    out.to_csv(PROCESSED_DIR / "population_projections.csv", index=False)
    return out


def build_provider_outputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    providers_path = INPUT_PROCESSED / "providers_by_lhin.csv"
    providers = pd.read_csv(providers_path)

    grouped = (
        providers.groupby(["lhin", "specialty", "population"], as_index=False)["physicians_count"].sum()
    )

    def by_specialty(df: pd.DataFrame, label: str) -> pd.Series:
        mask = df["specialty"].str.contains(label, case=False, na=False)
        return df.loc[mask].groupby("lhin")["physicians_count"].sum()

    gp = by_specialty(grouped, "family")
    spec = grouped.loc[~grouped["specialty"].str.contains("family", case=False, na=False)] \
        .groupby("lhin")["physicians_count"].sum()

    base = grouped[["lhin", "population"]].drop_duplicates(subset=["lhin"]).set_index("lhin")
    provider_out = base.copy()
    provider_out["gp_count"] = gp
    provider_out["spec_count"] = spec
    provider_out = provider_out.fillna(0).reset_index().rename(columns={"lhin": "LHIN"})
    provider_out["province"] = "Ontario"
    provider_out["year"] = 2024
    provider_out["total_physicians"] = provider_out["gp_count"] + provider_out["spec_count"]
    provider_out["gp_per_1000"] = (provider_out["gp_count"] / provider_out["population"] * 1000).round(3)
    provider_out["spec_per_1000"] = (provider_out["spec_count"] / provider_out["population"] * 1000).round(3)
    provider_out["np_count"] = 0.0
    provider_out["np_per_1000"] = 0.0

    provider_cols = [
        "LHIN",
        "province",
        "year",
        "gp_count",
        "spec_count",
        "np_count",
        "total_physicians",
        "gp_per_1000",
        "spec_per_1000",
        "np_per_1000",
        "population",
    ]
    provider_out = provider_out[provider_cols]
    provider_out.to_csv(PROCESSED_DIR / "providers_by_lhin.csv", index=False)

    np_out = provider_out[["LHIN", "province", "year", "np_count", "np_per_1000", "population"]].copy()
    np_out.to_csv(PROCESSED_DIR / "np_by_lhin.csv", index=False)

    return provider_out, np_out


def main() -> None:
    pop = build_population_by_age_lhin()
    proj = build_population_projections(pop)
    providers, nps = build_provider_outputs()

    print(f"Wrote {len(pop)} rows: data/processed/population_by_age_lhin.csv")
    print(f"Wrote {len(proj)} rows: data/processed/population_projections.csv")
    print(f"Wrote {len(providers)} rows: data/processed/providers_by_lhin.csv")
    print(f"Wrote {len(nps)} rows: data/processed/np_by_lhin.csv")


if __name__ == "__main__":
    main()
