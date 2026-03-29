# Dashboard Data Files - Complete Reference Guide

**Date:** March 28, 2026
**Purpose:** Comprehensive schema and usage guide for all dashboard data files
**Location:** `dashboard_data/` (layers 1-4) and `processed/` (model results)

---

## Overview: 4-Layer Architecture + Model Results

This dashboard uses a **4-layer data architecture** that separates:
1. **Population baseline** (who needs care)
2. **Current burden** (what's happening now in 2024)
3. **Predictive trajectory** (historical + projections: 2024/2029/2034)
4. **Cost analysis** (ROI and intervention economics)

Plus full **model results** for detailed scenario analysis.

---

## File 1: Layer 1 - Population Demographics

**File:** `dashboard_data/layer1_population_demographics.csv`
**Rows:** 1 (Ontario-wide)
**Purpose:** Baseline population and physician supply context

### Schema (9 columns)

| Column                             | Type    | Description                               | Example Value     |
| ---------------------------------- | ------- | ----------------------------------------- | ----------------- |
| `geography_level`                  | String  | Geographic aggregation level              | "Province"        |
| `geography_name`                   | String  | Name of geography                         | "Ontario"         |
| `population_2024`                  | Integer | Total population (2024)                   | 15,200,000        |
| `population_65plus`                | Integer | Population aged 65+                       | 2,690,400 (17.7%) |
| `median_age`                       | Float   | Median age                                | 41.3 years        |
| `total_physicians`                 | Integer | Total active physicians                   | 30,117            |
| `physicians_per_100k`              | Float   | Physician density                         | 198.1 per 100K    |
| `total_effective_capacity_fte`     | Float   | Effective clinical FTE (80% availability) | 31,069 FTE        |
| `rural_physician_density_estimate` | Integer | Estimated rural density                   | 180 per 100K      |
| `urban_physician_density_estimate` | Integer | Estimated urban density                   | 250 per 100K      |

### Data Sources

- **Population:** Statistics Canada 2021 Census + 2024 projections
- **Physicians:** Ontario Medical Association (OMA) 2024 Physician Census (47 specialties)
- **Effective capacity:** 80% clinical availability factor (20% admin/research/vacation)
- **Rural/urban split:** Estimated based on national averages (not real Ontario data)

### Key Conclusions

- **Ontario has 198 physicians per 100K** (national average: ~230 per 100K)
- **Urban-rural gap:** ~30-40% difference in physician density
- **Aging population:** 17.7% are 65+ (growing at 2.8%/year vs 1.5% overall)
- **Effective capacity:** 31,069 FTE available for clinical work (from 30,117 total)

### Dashboard Use

- **Baseline reference map:** Show Ontario population distribution
- **Physician density heatmap:** Compare urban vs rural density
- **Context for gap analysis:** Population growth drives demand

---

## File 2: Layer 2 - Current Burden (2024 Baseline)

**File:** `dashboard_data/layer2_current_burden.csv`
**Rows:** 8 (one per condition)
**Purpose:** What's happening NOW (2024 baseline state)

### Schema (22 columns)

#### Core Metrics (9 columns)
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `geography` | String | Geographic level | "Ontario" |
| `condition` | String | Health condition | "Pneumonia" |
| `year` | Integer | Baseline year | 2024 |
| `ed_visits` | Integer | ED visits in 2024 | 220,000 |
| `ed_visits_per_100k` | Float | Per capita ED rate | 1,447.4 per 100K |
| `admissions` | Integer | Hospital admissions | 1,154 |
| `admissions_per_100k` | Float | Per capita admission rate | 7.6 per 100K |
| `avg_cost_per_admission` | Float | Average cost | $16,785 |
| `total_cost` | Float | Total healthcare cost | $19.4M |

#### Avoidability Metrics (3 columns)
| Column                 | Type  | Description              | Example    |
| ---------------------- | ----- | ------------------------ | ---------- |
| `avoidability_pct`     | Float | % preventable (AHRQ PQI) | 0.30 (30%) |
| `avoidable_admissions` | Float | Preventable admissions   | 346.2      |
| `avoidable_cost`       | Float | Preventable cost         | $5.8M      |

#### Capacity Metrics (3 columns)
| Column                             | Type    | Description                    | Example   |
| ---------------------------------- | ------- | ------------------------------ | --------- |
| `effective_physician_capacity_fte` | Float   | Available specialty capacity   | 4,050 FTE |
| `num_specialties_involved`         | Integer | Number of treating specialties | 4         |
| `care_gap_score`                   | Float   | Gap metric (⚠️ INVALIDATED)    | 54.6      |

#### Fraser Institute Wait Times (7 columns) ← **NEW March 28, 2026**
| Column                           | Type   | Description                    | Example                                     |
| -------------------------------- | ------ | ------------------------------ | ------------------------------------------- |
| `specialist_wait_weeks_ontario`  | Float  | Ontario GP → specialist wait   | 10.7 weeks                                  |
| `specialist_wait_weeks_canada`   | Float  | Canada specialty-specific wait | 12.1 weeks                                  |
| `total_wait_weeks_canada`        | Float  | Full GP → treatment time       | 21.2 weeks                                  |
| `primary_specialty`              | String | Primary treating specialty     | "Internal Medicine"                         |
| `wait_time_change_1993_2025_pct` | Float  | Historical change              | 313% increase                               |
| `wait_time_confidence`           | String | Data confidence level          | "High", "Medium", "None"                    |
| `wait_time_data_source`          | String | Data source                    | "Fraser Institute 2025 - Internal Medicine" |

### Data Sources

- **ED visits & admissions:** CIHI ED Supplementary Data (2003-2021) + extrapolation to 2024
- **Costs:** CIHI Patient Cost Estimator (2017-2022 average)
- **Avoidability %:** AHRQ Prevention Quality Indicators (PQI) framework
- **Physician capacity:** OMA 2024 Census + specialty matching weights
- **Wait times:** Fraser Institute "Waiting Your Turn 2025" survey

### Key Conclusions

**Highest Volume (2024):**
1. Mental Health: 500K ED visits, 2,500 admissions, $30M total cost
2. Pneumonia: 220K ED visits, 1,154 admissions, $19.4M total cost
3. Type 2 Diabetes: 180K ED visits, 344 admissions, $4.9M total cost

**Highest Avoidability:**
1. COPD: 45% avoidable → $5.4M preventable cost
2. Hypertension: 42% avoidable → $966K preventable cost
3. Heart Failure: 40% avoidable → $2.7M preventable cost

**Wait Times (2024):**
- Ontario average: **10.7 weeks** GP → specialist (shortest in Canada)
- Internal Medicine: **12.1 weeks** (covers Heart Failure, COPD, CKD, Diabetes, Hypertension)
- **Wait times tripled since 1993** (+313%)
- **7 of 8 conditions validated** (only Psychiatry missing)

### Dashboard Use

- **Current burden heatmap:** Show ED visits and costs by condition
- **Avoidability analysis:** Filter by avoidability % to prioritize interventions
- **Wait time visualization:** Display specialist access barriers by condition
- **Condition comparison:** Compare volume, cost, and avoidability side-by-side

---

## File 3: Layer 3 - Predictive Trajectory

**File:** `dashboard_data/layer3_predictive_trajectory.csv`
**Rows:** 24 (8 conditions × 3 years)
**Purpose:** Historical baseline + projections (2024/2029/2034)

### Schema (10 columns)

| Column                 | Type    | Description                 | Example                                                |
| ---------------------- | ------- | --------------------------- | ------------------------------------------------------ |
| `condition`            | String  | Health condition            | "COPD"                                                 |
| `year`                 | Integer | Projection year             | 2024, 2029, 2034                                       |
| `scenario`             | String  | Scenario type               | "Historical", "Reference", "Optimistic", "Pessimistic" |
| `growth_rate_pct`      | Float   | Annual growth rate          | 2.50%                                                  |
| `data_source`          | String  | Where growth rate came from | "CIHI Patient Cost Estimator (DAD)"                    |
| `confidence`           | Float   | Data confidence (0-1 scale) | 0.6 (60%)                                              |
| `ed_visits`            | Float   | Projected ED visits         | 150,000                                                |
| `admissions`           | Float   | Projected admissions        | 760                                                    |
| `avoidable_admissions` | Float   | Preventable admissions      | 342                                                    |
| `avoidable_cost`       | Float   | Preventable cost            | $5.4M                                                  |

### Data Sources

- **Growth rates:** Data-driven from 18-year CIHI ED data (2003-2021) and 5-year hospitalization data (2017-2022)
- **2024 baseline:** Same as Layer 2 (actual ED volumes)
- **2029/2034 projections:** Compound annual growth rate applied to baseline
- **Confidence levels:** Based on data source quality (18-year data = high, estimates = low)

### Key Conclusions

**Fastest Growing Conditions (CAGR):**
1. Mental Health: +3.50%/year (estimated from crisis trends) → **$10.6M by 2034**
2. Heart Failure: +3.42%/year (18-year AMI proxy data) → **$3.7M by 2034**
3. COPD: +2.50%/year (COVID-adjusted) → **$6.9M by 2034**

**Flat Growth:**
1. Pneumonia: +0.11%/year (18 years of data - HIGHEST CONFIDENCE) → **$5.8M by 2034**

**Total Projected Burden (2034):**
- **1.82M ED visits** (+26% from 2024)
- **8,364 admissions** (+26% from 2024)
- **$40.1M avoidable costs** (+24% from 2024)

**Confidence Levels:**
- **High (95%):** Pneumonia, Heart Failure (18-year data)
- **Medium (60%):** COPD, CKD, Stroke (5-year data, COVID-adjusted)
- **Low (30-40%):** Mental Health, Diabetes, Hypertension (estimates)

### Dashboard Use

- **Trend charts:** Line charts showing 2024 → 2029 → 2034 trajectory
- **Year slider:** Allow users to toggle between years
- **Scenario comparison:** Compare Reference vs Optimistic vs Pessimistic (future feature)
- **Growth rate transparency:** Display data source and confidence for each condition
- **Overlay 2024 baseline:** Show current reality vs projections

### Important Note

⚠️ **Wait times NOT included in this file** because:
- File has projections for 2024/2029/2034
- Static 2024 wait times don't match projection years
- Future enhancement: Project wait times forward based on +313% historical trend

---

## File 4: Layer 4 - Cost Analysis & ROI

**File:** `dashboard_data/layer4_cost_analysis.csv`
**Rows:** 8 (one per condition)
**Purpose:** Economic burden analysis with ROI for interventions

### Schema (14 columns)

#### Cost Metrics (6 columns)
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `condition` | String | Health condition | "Mental Health" |
| `avg_cost_per_admission` | Float | Average admission cost | $12,000 |
| `admissions_2024` | Integer | Baseline admissions | 2,500 |
| `total_cost_2024` | Float | Total cost (2024) | $30M |
| `avoidable_admissions_2024` | Float | Preventable (2024) | 625 |
| `avoidable_cost_2024` | Float | Preventable cost (2024) | $7.5M |

#### Projection Metrics (2 columns)
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `avoidable_admissions_2034` | Float | Preventable (2034) | 882 |
| `avoidable_cost_2034` | Float | Preventable cost (2034) | $10.6M |

#### Intervention Economics (6 columns)
| Column                            | Type  | Description                         | Example |
| --------------------------------- | ----- | ----------------------------------- | ------- |
| `managed_care_cost_alternative`   | Float | Cost of preventive care per patient | $1,200  |
| `potential_savings_per_admission` | Float | Savings vs admission                | $10,800 |
| `savings_5yr`                     | Float | Total 5-year savings                | $14.8M  |
| `roi_5yr`                         | Float | 5-year return on investment         | 9.0x    |
| `savings_10yr`                    | Float | Total 10-year savings               | $24.3M  |
| `roi_10yr`                        | Float | 10-year return on investment        | 9.0x    |
|                                   |       |                                     |         |

### Data Sources

- **Costs:** CIHI Patient Cost Estimator (2017-2022 average by condition)
- **2034 projections:** Layer 3 growth rates applied
- **Managed care alternative:** 10% of admission cost (industry benchmark)
- **ROI calculation:** (Avoidable cost - Managed care investment) / Managed care investment

### Key Conclusions

**Highest ROI Conditions (10-year):**
1. Mental Health: 9.0x ROI, $24.3M savings
2. CKD: 9.0x ROI, $11.7M savings
3. COPD: 9.0x ROI, $13.4M savings

**Highest Absolute Savings (2024-2034):**
1. Mental Health: $10.6M preventable cost (2034)
2. COPD: $6.9M preventable cost (2034)
3. CKD: $6.1M preventable cost (2034)

**Total Economic Opportunity:**
- **$40.1M avoidable by 2034** (all 8 conditions)
- **10-year ROI: 8-9x** across most conditions
- **Intervention cost:** ~$4-5M total to prevent $40M in admissions

### Dashboard Use

- **ROI calculator:** Input intervention cost, show break-even and ROI
- **Cost burden heatmap:** Visualize avoidable costs by condition
- **2024 vs 2034 comparison:** Show baseline vs projected burden
- **Priority ranking:** Sort by ROI or absolute savings
- **Investment scenario modeling:** Test different intervention costs

### Important Note

⚠️ **Wait times NOT included in this file** because:
- Focus is on cost ROI calculations
- Wait times don't directly inform cost projections
- If needed, dashboard can reference Layer 2 for baseline context

---

## File 5: Predictive Model Results (Full Output)

**File:** `processed/predictive_model_v2_results_YYYYMMDD_HHMMSS.csv`
**Rows:** 48 (8 conditions × 2 years × 3 scenarios)
**Purpose:** Complete model output with all scenarios and projections

### Schema (16 columns)

#### Identifiers (4 columns)
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `condition` | String | Health condition | "Pneumonia" |
| `year` | Integer | Projection year | 2029, 2034 |
| `scenario` | String | Scenario type | "Reference", "Optimistic", "Pessimistic" |
| `growth_rate_pct` | Float | Annual disease growth | 0.11% |

#### Demand Projections (4 columns)
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `ed_visits` | Float | Projected ED visits | 221,213 |
| `admissions` | Float | Projected admissions | 1,160 |
| `avoidable_admissions` | Float | Preventable admissions | 348 |
| `avg_cost` | Float | Average admission cost | $16,785 |
| `avoidable_cost` | Float | Preventable cost | $5.8M |

#### Supply Projections (3 columns)
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `effective_capacity_fte` | Float | Physician capacity | 3,950 FTE |
| `capacity_per_100k` | Float | Per capita capacity | 26.0 per 100K |
| `net_change_fte` | Float | Change from 2024 | -100 FTE |

#### Gap Analysis (4 columns) ⚠️ **INVALIDATED**
| Column | Type | Description | Status |
|--------|------|-------------|--------|
| `required_capacity_fte` | Float | Needed capacity (INVALID) | ❌ Invalid |
| `capacity_gap_fte` | Float | Surplus/deficit (INVALID) | ❌ Invalid |
| `gap_ratio` | Float | Demand/supply ratio (INVALID) | ❌ Invalid |
| `gap_severity` | String | LOW/MODERATE/HIGH/CRITICAL | ❌ Invalid |

### Data Sources

- **Disease growth rates:** CIHI ED Supplementary (18-year) + Patient Cost Estimator (5-year)
- **Physician supply:** OMA 2024 Census
- **Attrition rates:** Scenario-dependent (Reference: 2.5%, Optimistic: 2.0%, Pessimistic: 3.0%)
- **New graduates:** Scenario-dependent (Reference: 2.0%, Optimistic: 2.5%, Pessimistic: 1.5%)

### Scenarios Explained

**Reference (Base Case):**
- Disease growth: Data-driven rates (0.11% to 3.50%)
- Physician attrition: 2.5%/year
- New graduates: 2.0%/year
- **Result:** -4.9% capacity by 2034 (-1,519 FTE)

**Optimistic:**
- Disease growth: Same as Reference (data-driven)
- Physician attrition: 2.0%/year (lower)
- New graduates: 2.5%/year (higher)
- **Result:** +5.1% capacity by 2034 (+1,589 FTE)

**Pessimistic:**
- Disease growth: Same as Reference (data-driven)
- Physician attrition: 3.0%/year (higher)
- New graduates: 1.5%/year (lower)
- **Result:** -14.0% capacity by 2034 (-4,358 FTE)

### Key Conclusions

**Disease Burden (Same Across All Scenarios):**
- Projections are **identical** across scenarios because disease growth is data-driven
- Scenarios only vary physician supply (attrition vs new grads)
- **2034 burden: 1.82M ED visits, $40.1M avoidable costs** (regardless of scenario)

**Physician Supply (Varies by Scenario):**
- **Reference:** Modest decline (-4.9%)
- **Optimistic:** Modest growth (+5.1%)
- **Pessimistic:** Significant decline (-14.0%)

**Critical Finding:**
- Even in **Optimistic scenario**, disease burden grows faster than physician supply
- **All scenarios show worsening burden** (demand +26%, supply -4.9% to +5.1%)

### Dashboard Use

- **Scenario comparison dropdown:** Toggle between Reference/Optimistic/Pessimistic
- **Full model output table:** Display all projections with filters
- **Detailed drill-down:** Click condition to see complete projection breakdown
- **Export functionality:** Allow users to download full results

### Important Notes

⚠️ **Gap ratio columns are INVALIDATED:**
- NPDB validation showed "200 cases per physician" assumption is off by 10-50x
- Gap ratios < 1.0 are mathematical artifacts
- DO NOT use `gap_ratio`, `gap_severity`, `required_capacity_fte`, `capacity_gap_fte` for analysis
- See `CAPACITY_ANALYSIS_FINDINGS.md` for complete validation

⚠️ **Wait times NOT included in this file** because:
- File has 2029/2034 projections
- Static 2024 wait times don't belong in projection rows
- Wait times should INFORM the model (replace gap_ratio), not be extra columns

---

## Data Quality Summary

### High Confidence Data (95%+)
- ✅ Pneumonia growth rate (18-year CIHI ED data)
- ✅ Heart Failure growth rate (18-year AMI proxy)
- ✅ Admission costs (CIHI Patient Cost Estimator 2017-2022)
- ✅ Fraser Institute wait times (7 of 8 conditions validated)

### Medium Confidence Data (60-75%)
- ⚠️ COPD, CKD, Stroke growth rates (5-year hospitalization, COVID-adjusted)
- ⚠️ Physician capacity allocation by specialty (clinical practice patterns)
- ⚠️ LHIN geographic distribution (proportional, not real data)

### Low Confidence Data (30-40%)
- ⚠️ Mental Health growth rate (estimated from crisis trends)
- ⚠️ Diabetes, Hypertension growth rates (demographic assumptions)
- ❌ Gap ratios (INVALIDATED by NPDB validation)

### Known Limitations

1. **No LHIN-level wait times:** Fraser data is provincial average (10.7 weeks Ontario), not LHIN-specific
2. **Mental Health wait times missing:** Psychiatry not included in Fraser Institute survey (1 of 8 conditions)
3. **LHIN results use proportional distribution:** Not true LHIN-level admission data
4. **Gap ratio analysis invalid:** "200 cases per physician" assumption off by 10-50x

---

## How to Use This Guide

### For Dashboard Developers:
1. **Start with Layer 2** for current state visualizations
2. **Use Layer 3** for trend charts and projections
3. **Use Layer 4** for ROI calculations and intervention planning
4. **Reference model results** for detailed scenario analysis
5. **AVOID gap ratio columns** - use wait times instead for access analysis

### For Data Analysts:
1. **Confidence levels** are in each file - filter accordingly
2. **Growth rates** are data-driven (not assumptions) - validate sources
3. **Wait times** are in Layer 2 only - reference Fraser files for details
4. **LHIN data** is proportional - do not use for policy decisions

### For Presenters:
1. **Lead with Layer 2** - $40.1M avoidable costs
2. **Show Layer 3 trends** - disease burden growing +26%
3. **Present Layer 4 ROI** - 8-9x return on investment
4. **Acknowledge limitations** - gap ratios invalid, LHIN data proportional
5. **Highlight Fraser validation** - 10.7 week wait times prove access constraints

---

## File Locations

**Dashboard Data (4 layers):**
```
dashboard_data/
├── layer1_population_demographics.csv    (1 row)
├── layer2_current_burden.csv             (8 rows - HAS WAIT TIMES)
├── layer3_predictive_trajectory.csv      (24 rows)
└── layer4_cost_analysis.csv              (8 rows)
```

**Model Results:**
```
processed/
└── predictive_model_v2_results_20260328_190119.csv  (48 rows)
```

**Additional Reference Files:**
```
processed/
├── fraser_institute_wait_times_2025.csv      (14 specialties)
├── condition_specialist_wait_times.csv       (8 conditions)
├── gap_conditions.csv                        (8 rows summary)
├── gap_regions.csv                           (14 LHINs)
└── actual_services_per_physician.csv         (23 specialties - NPDB validation)
```

**Documentation:**
```
FRASER_INSTITUTE_WAIT_TIMES_ANALYSIS.md       (Complete Fraser analysis)
CAPACITY_ANALYSIS_FINDINGS.md                 (NPDB + Fraser validation)
DASHBOARD_FILES_CHECKLIST.md                  (File transfer guide)
```

---

**Last Updated:** March 28, 2026
**Version:** 2.0 (includes Fraser Institute wait times validation)
**Contact:** Imran Yussuff
