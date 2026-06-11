#!/usr/bin/env python3
"""Medicaid ABD market sizing from public CMS data (data.medicaid.gov).

Pulls the TAF-based "Major Eligibility Group Information for Medicaid and
CHIP Beneficiaries by Month" dataset via the public API, extracts the Aged
and Persons-with-disabilities groups, and computes:

  - enrollment levels by state and month
  - month-over-month NET new enrollment (inflow minus outflow)
  - churn-adjusted GROSS new-case estimates (the market-sizing number)

No restricted access required. T-MSIS RIF via ResDAC refines new-vs-renewal
at person level; this public pipeline bounds the answer and refreshes monthly.

Usage:
  python main.py --states Texas Florida --out abd_summary.csv
  python main.py --all-states --out abd_summary.csv
"""
import argparse
import csv
import json
import sys
import urllib.parse
import urllib.request

DATASET = "ea9b7db3-db71-4663-b4e1-67e11d1d4fcc"  # major eligibility group by month
BASE = f"https://data.medicaid.gov/api/1/datastore/query/{DATASET}/0"
ABD_GROUPS = {"Aged", "Persons with disabilities"}

# Published Medicaid churn literature (MACPAC): monthly disenrollment among
# aged/disabled groups is low and re-enrollment within 12 months is common.
# Gross inflow = net change + replacement of leavers. This default monthly
# exit rate for ABD is conservative; casework calibrates it per state from
# the CMS Performance Indicator determinations data.
DEFAULT_MONTHLY_EXIT_RATE = 0.008


def fetch_page(offset, limit=500):
    params = urllib.parse.urlencode({"limit": limit, "offset": offset})
    req = urllib.request.Request(f"{BASE}?{params}",
                                 headers={"User-Agent": "abd-market-sizing/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def fetch_all(max_rows=None):
    rows, offset = [], 0
    while True:
        page = fetch_page(offset)
        batch = page.get("results", [])
        if not batch:
            break
        rows.extend(batch)
        offset += len(batch)
        total = page.get("count") or 0
        sys.stderr.write(f"\r  fetched {offset}/{total} rows")
        if max_rows and offset >= max_rows:
            break
        if offset >= total:
            break
    sys.stderr.write("\n")
    return rows


def to_int(s):
    s = (s or "").replace(",", "").strip()
    return int(s) if s.isdigit() else None


def analyze(rows, states=None, exit_rate=DEFAULT_MONTHLY_EXIT_RATE):
    """Return per state x month ABD enrollment, net new, gross-new estimate."""
    series = {}
    for r in rows:
        if r.get("majoreligibility_group") not in ABD_GROUPS:
            continue
        st = r.get("state")
        if states and st not in states:
            continue
        n = to_int(r.get("countenrolled"))
        if n is None or r.get("dunusable"):
            continue
        key = (st, r.get("month"))
        series.setdefault(key, {})[r["majoreligibility_group"]] = n

    out = []
    by_state = {}
    for (st, month), groups in sorted(series.items()):
        by_state.setdefault(st, []).append((month, groups))
    for st, months in by_state.items():
        prev_total = None
        for month, groups in months:
            total = sum(groups.values())
            net_new = (total - prev_total) if prev_total is not None else None
            # gross new = net change + estimated exits replaced
            gross_new = (net_new + round(prev_total * exit_rate)
                         if net_new is not None else None)
            out.append({
                "state": st, "month": month,
                "aged": groups.get("Aged"),
                "disabled": groups.get("Persons with disabilities"),
                "abd_total": total,
                "net_new": net_new,
                "gross_new_est": gross_new,
            })
            prev_total = total
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--states", nargs="*", help="state names (default: all)")
    ap.add_argument("--all-states", action="store_true")
    ap.add_argument("--exit-rate", type=float, default=DEFAULT_MONTHLY_EXIT_RATE,
                    help="assumed monthly ABD exit rate for gross-new estimate")
    ap.add_argument("--out", default="abd_summary.csv")
    args = ap.parse_args()

    states = None if (args.all_states or not args.states) else set(args.states)
    print("[1/3] fetching public TAF eligibility-group data (data.medicaid.gov)")
    rows = fetch_all()
    print(f"[2/3] computing ABD series (exit rate {args.exit_rate:.1%}/month)")
    table = analyze(rows, states=states, exit_rate=args.exit_rate)
    if not table:
        print("no rows matched - check state names")
        sys.exit(2)
    print(f"[3/3] writing {len(table)} state-months -> {args.out}")
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0].keys()))
        w.writeheader()
        w.writerows(table)

    # console summary: latest month per state
    latest = {}
    for row in table:
        if row["gross_new_est"] is not None:
            latest[row["state"]] = row
    print("\nLatest month with usable data, per state:")
    for st in sorted(latest):
        r = latest[st]
        print(f"  {st:<22} {r['month']}  ABD={r['abd_total']:>9,}  "
              f"net_new={r['net_new']:>7,}  gross_new_est={r['gross_new_est']:>7,}")


if __name__ == "__main__":
    main()
