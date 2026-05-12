import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

_api_key = os.environ.get("FMP_API_KEY")
if not _api_key:
    print("[fmp] ERROR: FMP_API_KEY not set — add it to .env in the project root", file=sys.stderr)
    sys.exit(1)

print("[fmp] FMP MCP server ready", file=sys.stderr)

from mcp.server.fastmcp import FastMCP
from tools import FMPNoDataError, FMPPremiumError, get_ratios as _get_ratios

mcp = FastMCP("fmp")


@mcp.tool()
def get_ratios(ticker: str) -> dict:
    """Valuation ratios for a ticker: pe_ratio, ps_ratio, ev_ebitda, pfcf, ev_revenue."""
    return _get_ratios(ticker, _api_key)


if __name__ == "__main__":
    mcp.run()
