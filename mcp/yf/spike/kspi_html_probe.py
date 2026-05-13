"""Spike: probe KSPI Yahoo HTML pages using curl_cffi (Chrome impersonation).

Throwaway exploration. Confirms which fields are reachable from
`/quote/{TICKER}/key-statistics/` and `/quote/{TICKER}/` and resolves Open
Question 1 (does the page expose `financialCurrency` / currency banner?).
"""
import sys
from curl_cffi import requests as creq
from bs4 import BeautifulSoup


def fetch(url: str) -> BeautifulSoup:
    r = creq.get(url, impersonate="chrome", timeout=10)
    print(f"GET {url} -> {r.status_code} ({len(r.text)} bytes)", file=sys.stderr)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def dump_kv_rows(soup: BeautifulSoup, label: str) -> None:
    print(f"\n=== {label}: all tr rows ===", file=sys.stderr)
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if 2 <= len(cells) <= 4 and any(cells):
            print("  | ".join(cells), file=sys.stderr)


def probe_currency(soup: BeautifulSoup, label: str) -> None:
    print(f"\n=== {label}: currency probe ===", file=sys.stderr)
    text = soup.get_text(" ", strip=True)
    for needle in ("Currency in", "KZT", "USD", "EUR", "Financial Currency"):
        i = 0
        while True:
            idx = text.find(needle, i)
            if idx < 0:
                break
            print(f"  '{needle}' @{idx}: ...{text[max(0,idx-30):idx+60]}...", file=sys.stderr)
            i = idx + 1
            if i - idx > 400:
                break


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "KSPI"
    keystats = fetch(f"https://finance.yahoo.com/quote/{ticker}/key-statistics/")
    quote = fetch(f"https://finance.yahoo.com/quote/{ticker}/")
    dump_kv_rows(keystats, f"{ticker} key-statistics")
    probe_currency(keystats, f"{ticker} key-statistics")
    probe_currency(quote, f"{ticker} quote summary")
