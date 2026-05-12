"""Followup probes: real segments check + explicit SBC row + revisions deeper look."""
import warnings
import yfinance as yf

warnings.filterwarnings("ignore")

for tk in ["NVDA", "META", "RDDT"]:
    t = yf.Ticker(tk)
    print(f"\n===== {tk} =====")

    # check for segments attributes
    seg_attrs = [a for a in dir(t) if "segment" in a.lower()]
    print(f"segment-like attrs: {seg_attrs}")

    # explicit SBC value from cashflow
    try:
        cf = t.cashflow
        if "Stock Based Compensation" in cf.index:
            sbc = cf.loc["Stock Based Compensation"]
            print(f"SBC row (annual): {sbc.to_dict()}")
        else:
            print("SBC row absent from annual cashflow")
        qcf = t.quarterly_cashflow
        if "Stock Based Compensation" in qcf.index:
            print(f"SBC quarterly cols: {list(qcf.columns)}")
            print(f"SBC quarterly: {qcf.loc['Stock Based Compensation'].to_dict()}")
        else:
            print("SBC absent from quarterly cashflow")
    except Exception as e:
        print(f"SBC check failed: {e}")

    # quarterly earnings history for 8q SUE
    try:
        eh = t.earnings_history
        print(f"earnings_history rows: {len(eh) if eh is not None else 0}")
    except Exception as e:
        print(f"earnings_history failed: {e}")

    # upgrades_downgrades freshness
    try:
        ud = t.upgrades_downgrades
        if ud is not None and not ud.empty:
            latest = ud.index.max()
            print(f"upgrades_downgrades latest: {latest}, count: {len(ud)}")
    except Exception as e:
        print(f"upgrades_downgrades failed: {e}")

    # info top-level keys that might carry segments / guidance
    info = t.info
    seg_keys = [k for k in info.keys() if "segment" in k.lower() or "guidance" in k.lower() or "outlook" in k.lower()]
    print(f"info seg/guidance keys: {seg_keys}")
