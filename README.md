# Medicaid ABD Market Sizing (Public CMS Data)

Quantify the Aged, Blind, and Disabled (ABD) Medicaid population and estimate
new-case volume by state - from public CMS data, no restricted access needed.

Pulls the TAF-based **"Major Eligibility Group Information for Medicaid and
CHIP Beneficiaries by Month"** dataset from the data.medicaid.gov public API,
extracts the Aged and Persons-with-disabilities eligibility groups, and
computes per state and month:

- ABD enrollment levels (Aged / Disabled split)
- Month-over-month **net new** enrollment
- Churn-adjusted **gross new-case estimates** (net change + replaced exits)

## Run it

```bash
# stdlib only - no dependencies
python main.py --states Texas Florida California --out abd_summary.csv
python main.py --all-states --out abd_summary.csv
```

Sample output (live API, December 2022, default 0.8%/month exit rate):

```
California   202212  ABD=2,358,685  net_new=4,062  gross_new_est=22,899
Florida      202212  ABD=1,394,909  net_new=3,363  gross_new_est=14,495
Texas        202212  ABD=1,228,537  net_new=  807  gross_new_est=10,629
```

## Methodology notes

- **Net vs gross new cases**: enrollment deltas give net change only. Gross
  inflow (the market-sizing number) = net change + exits replaced. The
  monthly exit rate is calibrated per state from the CMS Performance
  Indicator eligibility-determinations data; the default here is a
  conservative placeholder.
- **Blind category**: public TAF groups fold blind into the disability
  group. A separate blind breakout requires state aid-code data
  (several states publish it) or T-MSIS RIF access.
- **LTSS/HCBS/nursing-home split**: layered in from the MLTSS enrollees
  dataset (same API), MDS-based nursing-home admissions, and state HCBS
  waiver reports.
- **Refresh**: the script is idempotent and API-driven - schedule it monthly.

## Where restricted data would improve this

Person-level new-vs-renewal distinction, county-level breakdowns, and exact
blind/disabled separation are sharper with T-MSIS TAF Research Identifiable
Files via a ResDAC DUA (a months-long application process with fees). This
public pipeline bounds the answer now and stays as the refresh layer later.
