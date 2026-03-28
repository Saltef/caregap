import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
META_FILE = ROOT / "data" / "metadata.json"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

DATASETS = [
    {
        "key": "population_by_age_lhin",
        "title": "Population by age and LHIN",
        "method": "Auto-fetch",
        "source": "Statistics Canada table 17-10-0142",
        "file": "population_by_age_lhin.csv",
        "required_cols": ["LHIN", "year", "age_group", "population"],
    },
    {
        "key": "population_projections",
        "title": "Population projections",
        "method": "Auto-fetch",
        "source": "Statistics Canada table 17-10-0057",
        "file": "population_projections.csv",
        "required_cols": ["year", "age_group", "population"],
    },
    {
        "key": "providers_by_lhin",
        "title": "Physicians by LHIN",
        "method": "Manual upload",
        "source": "CIHI physicians report",
        "file": "providers_by_lhin.csv",
        "required_cols": ["LHIN", "year", "gp_count"],
    },
    {
        "key": "np_by_lhin",
        "title": "Nurse practitioners by LHIN",
        "method": "Manual upload",
        "source": "CIHI regulated nurses report",
        "file": "np_by_lhin.csv",
        "required_cols": ["LHIN", "year", "np_count"],
    },
    {
        "key": "hospitalizations_by_lhin",
        "title": "Hospitalizations by LHIN",
        "method": "Manual upload",
        "source": "CIHI quick stats",
        "file": "hospitalizations_by_lhin.csv",
        "required_cols": ["LHIN", "year", "hospitalizations"],
    },
]


def _load_metadata() -> dict:
    if not META_FILE.exists():
        return {}
    try:
        return json.loads(META_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _format_timestamp(value: str | None) -> str:
    if not value:
        return "Not loaded"
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return ts.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return value


def _validate_dataset(spec: dict, meta: dict) -> tuple[bool, int, list[str], str]:
    issues = []
    path = PROCESSED_DIR / spec["file"]
    if not path.exists():
        return False, 0, ["File not found"], "Not loaded"

    row_count = 0
    try:
        df = pd.read_csv(path)
        row_count = len(df)
        missing = [c for c in spec["required_cols"] if c not in df.columns]
        if missing:
            issues.append(f"Missing columns: {missing}")
    except Exception as exc:
        issues.append(f"Failed to parse file: {exc}")

    entry = meta.get(spec["key"], {})
    last_updated = _format_timestamp(entry.get("last_updated"))
    issues.extend(entry.get("issues", []))
    return len(issues) == 0, row_count, issues, last_updated


def _render_status_cards() -> None:
    st.subheader("Dataset Status")
    meta = _load_metadata()

    for spec in DATASETS:
        ok, rows, issues, last_updated = _validate_dataset(spec, meta)
        if ok:
            st.success(
                f"{spec['title']} ({spec['method']})\n\nRows: {rows} | Updated: {last_updated}"
            )
        else:
            st.warning(
                f"{spec['title']} ({spec['method']})\n\nRows: {rows} | Updated: {last_updated}"
            )
            for issue in issues:
                st.caption(f"- {issue}")


def _save_uploaded_file(uploaded_file) -> Path:
    save_path = RAW_DIR / uploaded_file.name
    save_path.write_bytes(uploaded_file.getbuffer())
    return save_path


st.title("Data Manager")
st.write("Fetch StatsCan data or upload CIHI files to build the processed datasets.")

_render_status_cards()

st.divider()
col_auto, col_manual = st.columns([1, 1], gap="large")

with col_auto:
    st.subheader("Auto-fetch: Statistics Canada")
    st.write("Downloads and processes population datasets into `data/processed/`.")

    if st.button("Fetch from Statistics Canada", type="primary", use_container_width=True):
        from fetch.statcan import fetch_all

        with st.spinner("Fetching and processing data..."):
            fetch_all()
        st.success("StatsCan datasets updated.")
        st.rerun()

    pop_path = PROCESSED_DIR / "population_by_age_lhin.csv"
    if pop_path.exists():
        with st.expander("Preview: population_by_age_lhin.csv"):
            st.dataframe(pd.read_csv(pop_path).head(10), use_container_width=True)

with col_manual:
    st.subheader("Manual upload: CIHI")
    provider_tab, np_tab, hosp_tab = st.tabs(
        ["L1 Providers", "L1 Nurse Practitioners", "L2 Hospitalizations"]
    )

    with provider_tab:
        provider_file = st.file_uploader(
            "Upload physicians file (.xlsx or .csv)", type=["xlsx", "csv"], key="provider_up"
        )
        if provider_file is not None:
            from fetch.cihi_loader import load_providers

            with st.spinner("Saving and normalizing providers file..."):
                save_path = _save_uploaded_file(provider_file)
                out = load_providers(filepath=save_path)

            if out is None:
                st.error("Could not normalize provider file. Check the source sheet/columns.")
            else:
                st.success(f"Providers loaded: {len(out)} rows.")
                st.rerun()

    with np_tab:
        np_file = st.file_uploader(
            "Upload nurse practitioners file (.xlsx or .csv)",
            type=["xlsx", "csv"],
            key="np_up",
        )
        if np_file is not None:
            from fetch.cihi_loader import load_nurse_practitioners

            with st.spinner("Saving and normalizing NP file..."):
                save_path = _save_uploaded_file(np_file)
                out = load_nurse_practitioners(filepath=save_path)

            if out is None:
                st.error("Could not normalize NP file. Check the source sheet/columns.")
            else:
                st.success(f"Nurse practitioner rows loaded: {len(out)}.")
                st.rerun()

    with hosp_tab:
        hosp_file = st.file_uploader(
            "Upload hospitalization file (.xlsx or .csv)",
            type=["xlsx", "csv"],
            key="hosp_up",
        )
        if hosp_file is not None:
            from utils.data_store import process_cihi_upload

            with st.spinner("Saving and normalizing hospitalization file..."):
                ok = process_cihi_upload(hosp_file)

            if ok:
                st.success("Hospitalization file integrated.")
                st.rerun()
            else:
                st.error("Failed to parse hospitalization file. Check column headers.")

st.divider()
st.subheader("Validation Summary")

validation_rows = []
metadata = _load_metadata()
for spec in DATASETS:
    ok, rows, issues, last_updated = _validate_dataset(spec, metadata)
    validation_rows.append(
        {
            "dataset": spec["key"],
            "status": "ok" if ok else "issue",
            "rows": rows,
            "updated": last_updated,
            "issues": "; ".join(issues),
        }
    )

st.dataframe(pd.DataFrame(validation_rows), use_container_width=True, hide_index=True)
