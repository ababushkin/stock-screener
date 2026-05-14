"""Collect frozen historical fixtures for the engagement-KPI backtest (ABA-66 Task 6 Slice B).

For each (ticker, quarter):
  Leg 1 - Pull 8-K Exhibit 99.1 from EDGAR, extract KPI YoY change.
  Leg 2 - Pull wayback snapshots of finance.yahoo.com/quote/<T>/analysis/ at T0 (print+0-3d)
          and T1 (print+~28d, +-7d) and extract "Next Year" avg revenue estimate.

Writes one JSON fixture per ticker-quarter to tests/fixtures/engagement_kpi/<ticker>_<period>.json.
Backtest harness (Slice C) reads those fixtures and asserts >=60% direction agreement on >=24 samples.

Run: python3 tests/spike/collect_backtest_fixtures.py [--ticker META]

The harness is deliberately verbose - it skips on extraction failure rather than crashing, and
records the failure mode in the fixture so Slice C can report attrition.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIX_DIR = REPO / "tests" / "fixtures" / "engagement_kpi"
UA = "Stock Review Skill-Pack babushkin.anton@gmail.com"

# Earnings 8-K filings per ticker, identified by date pattern (Jan/Apr/Jul/Oct +- 1mo).
# Accession + filing_date pulled from EDGAR submissions API on 2026-05-14.
# Excludes non-earnings 8-Ks (special dividends, leadership changes, etc.).
EARNINGS_8K = {
    "META": [
        ("Q1-2026", "0001628280-26-028364", "2026-04-29"),
        ("Q4-2025", "0001628280-26-003832", "2026-01-28"),
        ("Q3-2025", "0001628280-25-047114", "2025-10-29"),
        ("Q2-2025", "0001628280-25-036719", "2025-07-30"),
        ("Q1-2025", "0001326801-25-000050", "2025-04-30"),
        ("Q4-2024", "0001326801-25-000014", "2025-01-29"),
        ("Q3-2024", "0001326801-24-000077", "2024-10-30"),
        ("Q2-2024", "0001326801-24-000065", "2024-07-31"),
        # Q1 2024 and earlier: paginate older filings; out of scope for first pass.
    ],
    "RDDT": [
        ("Q1-2026", "0001713445-26-000067", "2026-04-30"),
        ("Q4-2025", "0001713445-26-000020", "2026-02-05"),
        ("Q3-2025", "0001713445-25-000225", "2025-10-30"),
        ("Q2-2025", "0001713445-25-000194", "2025-07-31"),
        ("Q1-2025", "0001713445-25-000100", "2025-05-01"),
        ("Q4-2024", "0001713445-25-000016", "2025-02-12"),
        ("Q3-2024", "0001713445-24-000099", "2024-10-29"),
        ("Q2-2024", "0001713445-24-000052", "2024-08-06"),
        ("Q1-2024", "0001713445-24-000003", "2024-05-07"),
    ],
    "PINS": [
        ("Q1-2026", "0001506293-26-000066", "2026-05-04"),
        ("Q4-2025", "0001506293-26-000009", "2026-01-27"),
        ("Q3-2025", "0001506293-25-000228", "2025-11-04"),
        ("Q2-2025", "0001506293-25-000195", "2025-08-07"),
        ("Q1-2025", "0001506293-25-000106", "2025-05-08"),
        ("Q4-2024", "0001506293-25-000020", "2025-02-06"),
        # Older PINS earnings 8-Ks: paginate; first pass goes 5 quarters deep.
    ],
}

CIK = {"META": "0001326801", "RDDT": "0001713445", "PINS": "0001506293"}

# Per-ticker KPI extraction patterns. Anchored on label, tolerant of formatting drift across years.
KPI_PATTERNS = {
    "META": re.compile(
        r"(?:DAP|Family daily active people)[^.]*?"
        r"(?:was|of)\s+([0-9]+\.[0-9]+)\s+billion"
        r"[^.]*?(?:increase|increased)\s+of\s+([0-9]+(?:\.[0-9]+)?)%",
        re.IGNORECASE,
    ),
    "RDDT": re.compile(
        r"Daily Active Uniques[^.]*?"
        r"(?:increased|grew)\s+([0-9]+(?:\.[0-9]+)?)%[^.]*?"
        r"to\s+([0-9]+(?:\.[0-9]+)?)\s+million",
        re.IGNORECASE | re.DOTALL,
    ),
    "PINS": re.compile(
        r"Global Monthly Active Users[^.]*?"
        r"(?:increased|grew)\s+([0-9]+(?:\.[0-9]+)?)%[^.]*?"
        r"to\s+([0-9]+(?:\.[0-9]+)?)\s+million",
        re.IGNORECASE | re.DOTALL,
    ),
}


def fetch(url: str, timeout: int = 60, retries: int = 3) -> str:
    """Fetch URL with SEC-compliant UA. Retries on transient failures (5xx, curl errors)."""
    last_err = ""
    for attempt in range(retries):
        result = subprocess.run(
            ["curl", "-sS", "-fL", "-A", UA, url],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout
        last_err = result.stderr[:200]
        time.sleep(2 ** attempt)  # 1s, 2s, 4s
    raise RuntimeError(f"curl failed for {url} after {retries} retries: {last_err}")


def normalize(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text)


def find_ex991_url(ticker: str, accession: str) -> str:
    """Find Exhibit 99.1 URL inside an 8-K filing index."""
    acc_nodash = accession.replace("-", "")
    cik_int = int(CIK[ticker])
    index_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={CIK[ticker]}&type=8-K&dateb=&owner=include&count=40"
    # Easier path: hit the filing-index JSON directly.
    idx = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/"
    body = fetch(idx + "index.json")
    j = json.loads(body)
    for item in j["directory"]["item"]:
        name = item["name"].lower()
        if ("ex99" in name or "exhibit99" in name or "ex-99" in name or "press" in name) and name.endswith((".htm", ".html")):
            return idx + item["name"]
    # Fallback: take any .htm with "991" or "ex991" in it
    for item in j["directory"]["item"]:
        name = item["name"].lower()
        if "991" in name and name.endswith((".htm", ".html")):
            return idx + item["name"]
    raise RuntimeError(f"No Ex 99.1 found in {accession}")


def extract_kpi(ticker: str, ex991_url: str) -> dict:
    raw = fetch(ex991_url)
    text = normalize(raw)
    pat = KPI_PATTERNS[ticker]
    m = pat.search(text)
    if not m:
        # Save a snippet around 'DAP'/'Daily Active'/'Monthly Active' for debugging.
        probe = {"META": "DAP", "RDDT": "Daily Active Uniques", "PINS": "Monthly Active Users"}[ticker]
        idx = text.lower().find(probe.lower())
        snippet = text[max(0, idx-50): idx+250] if idx >= 0 else "<probe-not-found>"
        return {"status": "extraction_failed", "probe_snippet": snippet}
    if ticker == "META":
        kpi_value = float(m.group(1))
        yoy = float(m.group(2)) / 100
    else:  # RDDT, PINS - groups: yoy%, kpi_value
        yoy = float(m.group(1)) / 100
        kpi_value = float(m.group(2))
    return {
        "status": "ok",
        "kpi_value": kpi_value,
        "yoy_change": round(yoy, 4),
        "direction": 1 if yoy > 0 else (-1 if yoy < 0 else 0),
    }


NEXT_YEAR_PATTERNS = [
    # Wayback-rendered Yahoo: look for "Next Year (YYYY)" then "Avg. Estimate" then dollar value
    re.compile(
        r"Next Year[^A-Za-z]*\(([0-9]{4})\)[^<]*?Avg(?:\.|\s+)+Estimate[^<]*?\$?([0-9]+\.[0-9]+)\s*(B|M|T)",
        re.IGNORECASE | re.DOTALL,
    ),
    # Permissive: Revenue Estimate ... Next Year ... numeric
    re.compile(
        r"Revenue Estimate.*?Next Year[^0-9]*\(?([0-9]{4})\)?.*?Avg(?:\.|\s+)*Estimate[^0-9]*([0-9]+\.[0-9]+)\s*(B|M|T)",
        re.IGNORECASE | re.DOTALL,
    ),
]


def parse_yahoo_estimate(text: str) -> dict | None:
    """Return {'year': int, 'avg_estimate_usd': float} or None."""
    for pat in NEXT_YEAR_PATTERNS:
        m = pat.search(text)
        if m:
            year = int(m.group(1))
            val = float(m.group(2))
            unit = m.group(3).upper()
            scale = {"B": 1e9, "M": 1e6, "T": 1e12}[unit]
            return {"year": year, "avg_estimate_usd": val * scale}
    return None


def wayback_snapshot_url(target_url: str, target_date: str, retries: int = 3) -> tuple[str, str] | None:
    """Return (snapshot_url, snapshot_ts) for the closest wayback capture, or None.

    Retries on transient errors. Returns None only when wayback responds successfully
    and there is genuinely no snapshot.
    """
    ts = target_date.replace("-", "")
    probe = f"https://web.archive.org/web/{ts}/{target_url}"
    for attempt in range(retries):
        result = subprocess.run(
            ["curl", "-sS", "-I", "-A", UA, probe],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            # Look for Location header in 302 response, or accept 200 if it's a direct hit.
            location = None
            for line in result.stdout.splitlines():
                if line.lower().startswith("location:"):
                    location = line.split(":", 1)[1].strip()
                    break
            if not location:
                # Wayback responded but no redirect = no snapshot exists at this date.
                return None
            m = re.match(r"https?://web\.archive\.org/web/([0-9]{14})/", location)
            if not m:
                return None
            return location, m.group(1)
        time.sleep(2 ** attempt)
    return None  # all retries exhausted


DRIFT_TOLERANCE_DAYS = {"t0": 7, "t1": 14}


def fetch_revisions(ticker: str, print_date: str) -> dict:
    """Pull T0 and T1 Yahoo analysis-page revenue estimates from wayback."""
    pd = datetime.strptime(print_date, "%Y-%m-%d")
    t0_target = (pd + timedelta(days=1)).strftime("%Y-%m-%d")
    t1_target = (pd + timedelta(days=28)).strftime("%Y-%m-%d")
    yahoo_url = f"https://finance.yahoo.com/quote/{ticker}/analysis/"
    out = {"t0_target": t0_target, "t1_target": t1_target}
    for label, target in [("t0", t0_target), ("t1", t1_target)]:
        snap = wayback_snapshot_url(yahoo_url, target)
        if not snap:
            out[label] = {"status": "no_snapshot"}
            continue
        snap_url, snap_ts = snap
        snap_d = datetime.strptime(snap_ts[:8], "%Y%m%d")
        drift_days = abs((snap_d - datetime.strptime(target, "%Y-%m-%d")).days)
        if drift_days > DRIFT_TOLERANCE_DAYS[label]:
            out[label] = {"status": "drift_too_large", "snap_ts": snap_ts, "drift_days": drift_days}
            continue
        try:
            raw = fetch(snap_url, timeout=90)
        except Exception as e:
            out[label] = {"status": "fetch_failed", "error": str(e)[:200], "snap_url": snap_url}
            continue
        text = normalize(raw)
        parsed = parse_yahoo_estimate(text)
        if not parsed:
            out[label] = {"status": "parse_failed", "snap_url": snap_url, "snap_ts": snap_ts}
            continue
        out[label] = {
            "status": "ok", "snap_ts": snap_ts, "snap_url": snap_url,
            "drift_days": drift_days, **parsed,
        }
        time.sleep(1.0)  # be polite to wayback
    return out


def revision_signal(rev: dict) -> dict:
    """Compute revision direction from T0 -> T1 if both legs ok."""
    t0, t1 = rev.get("t0", {}), rev.get("t1", {})
    if t0.get("status") != "ok" or t1.get("status") != "ok":
        return {"status": "incomplete"}
    if t0["year"] != t1["year"]:
        return {"status": "year_label_drift", "t0_year": t0["year"], "t1_year": t1["year"]}
    pct = (t1["avg_estimate_usd"] - t0["avg_estimate_usd"]) / t0["avg_estimate_usd"]
    return {
        "status": "ok",
        "year": t0["year"],
        "t0_est_usd": t0["avg_estimate_usd"],
        "t1_est_usd": t1["avg_estimate_usd"],
        "revision_pct": round(pct, 5),
        "direction": 1 if pct > 0 else (-1 if pct < 0 else 0),
    }


def collect_one(ticker: str, period: str, accession: str, filing_date: str) -> dict:
    print(f"  {ticker} {period} ({filing_date}) ... ", end="", flush=True)
    fixture = {
        "ticker": ticker, "period": period,
        "accession": accession, "filing_date": filing_date,
    }
    try:
        ex991 = find_ex991_url(ticker, accession)
        fixture["ex991_url"] = ex991
        time.sleep(0.2)  # SEC politeness
        fixture["kpi"] = extract_kpi(ticker, ex991)
    except Exception as e:
        fixture["kpi"] = {"status": "error", "error": str(e)[:200]}
    time.sleep(0.2)
    try:
        rev = fetch_revisions(ticker, filing_date)
        fixture["revisions"] = rev
        fixture["signal"] = revision_signal(rev)
    except Exception as e:
        fixture["revisions"] = {"status": "error", "error": str(e)[:200]}
        fixture["signal"] = {"status": "error"}
    status_marks = []
    status_marks.append("K" if fixture["kpi"].get("status") == "ok" else "k")
    status_marks.append("R" if fixture.get("signal", {}).get("status") == "ok" else "r")
    print("".join(status_marks))
    return fixture


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", help="Restrict to a single ticker")
    ap.add_argument("--smoke", action="store_true", help="Only fetch the first sample per ticker")
    args = ap.parse_args()

    FIX_DIR.mkdir(parents=True, exist_ok=True)
    tickers = [args.ticker] if args.ticker else list(EARNINGS_8K.keys())
    all_fixtures = []
    for t in tickers:
        if t not in EARNINGS_8K:
            print(f"unknown ticker {t}", file=sys.stderr); return 2
        print(f"{t}:")
        items = EARNINGS_8K[t][:1] if args.smoke else EARNINGS_8K[t]
        for period, accession, filing_date in items:
            fix = collect_one(t, period, accession, filing_date)
            out = FIX_DIR / f"{t}_{period}.json"
            out.write_text(json.dumps(fix, indent=2) + "\n")
            all_fixtures.append(fix)

    ok_k = sum(1 for f in all_fixtures if f["kpi"].get("status") == "ok")
    ok_r = sum(1 for f in all_fixtures if f["signal"].get("status") == "ok")
    ok_both = sum(1 for f in all_fixtures if f["kpi"].get("status") == "ok" and f["signal"].get("status") == "ok")
    print(f"\nTotal: {len(all_fixtures)}  KPI ok: {ok_k}  Revision ok: {ok_r}  Both ok: {ok_both}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
