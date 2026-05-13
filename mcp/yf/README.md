# yf MCP server

Wraps `yfinance` and a Yahoo HTML scrape fallback (for tickers like KSPI whose
`Ticker.info` payload is missing valuation fields) behind an MCP tool surface.

## Install

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

## Run the server

```bash
.venv/bin/python server.py
```

## Tests

Hermetic suite (every commit):

```bash
.venv/bin/pytest -m "not nightly"
```

Nightly suite (hits live Yahoo — run on a schedule, not on every commit):

```bash
.venv/bin/pytest -m nightly
```

See `docs/design-docs/yf-ratios-html-fallback/` for the HTML-fallback design
and `tests/test_get_ratios.py` for the fitness functions backing each NFR.
