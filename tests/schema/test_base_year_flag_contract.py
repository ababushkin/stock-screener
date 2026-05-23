"""Contract tests for `meta.base_year_flag` + `scenarios.*.y2_5_cagr_source` (ABA-134).

The base-year-effect guard (SKILL.md COMPUTE Step 3a on the ESTABLISHED path,
Step 1a on the pre-profit path) detects a trailing CAGR distorted by a depressed
lookback base year and *halts* for operator confirmation rather than substituting
silently. It writes a `base_year_flag` block under the report's top-level `meta`
(every run, for audit symmetry) and a `y2_5_cagr_source` tag on each scenario.

These are pure-data tests on the documented JSON contract and the detection /
suggestion / confidence-cap logic. They do not run the live DCF — that is the
interactive acceptance step against `reports/NVDA_20260514.json`.

Covers:

- **Detection (D1 ∨ D2)** — OR-composite, path-tuned ceilings (FCF 0.40 /
  revenue 0.50) and a shared 0.15 base-year-ratio threshold; tripwire string
  encodes which signal(s) fired.
- **Threshold calibration** — the 0.15 ratio threshold does not false-trip a
  genuinely sustained 50–60% CAGR (the ABA-104 spike's reject-D5 table).
- **Suggested replacement** — `min(default_cap, playbook.growth_ceiling)`.
- **Artefact shape** — emitted every run; tripped/confirmed invariants;
  declined / non-interactive ⇒ no IV ⇒ no confidence cap.
- **y2_5_cagr_source** — enum + consistency with the flag.
- **Confidence cap** — confirmed trip caps `meta.confidence` at MEDIUM (one-way).
"""
import pytest


# ---------------------------------------------------------------------------
# Published constants (SKILL.md COMPUTE Step 3a / 1a — do not retune inline)
# ---------------------------------------------------------------------------

D1_CEILING = {"established": 0.40, "pre_profit": 0.50}
D2_RATIO_THRESHOLD = 0.15
DEFAULT_CAP = {"established": 0.25, "pre_profit": 0.30}

TRIPWIRE_ENUM = {"abs_cagr_40", "abs_cagr_50", "base_year_ratio_15", "abs_cagr+ratio", None}
SUGGESTION_SOURCE_ENUM = {"playbook_ceiling", "default_cap", "operator_override", None}
Y2_5_CAGR_SOURCE_ENUM = {
    "mechanical",
    "operator_confirmed_cap",
    "playbook_ceiling",
    "operator_override",
}
CONFIDENCE_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


# ---------------------------------------------------------------------------
# Detection + suggestion + confidence logic under test
# ---------------------------------------------------------------------------

def detect(cagr_3y, base_year_ratio, path):
    """Mirrors COMPUTE Step 3a/1a detection. Returns (tripped, tripwire)."""
    assert path in ("established", "pre_profit")
    d1 = cagr_3y > D1_CEILING[path]
    d2 = base_year_ratio < D2_RATIO_THRESHOLD
    tripped = d1 or d2
    if not tripped:
        tripwire = None
    elif d1 and d2:
        tripwire = "abs_cagr+ratio"
    elif d1:
        tripwire = "abs_cagr_40" if path == "established" else "abs_cagr_50"
    else:
        tripwire = "base_year_ratio_15"
    return tripped, tripwire


def resolve_suggestion(path, playbook_growth_ceiling=None):
    """Mirrors the suggested-replacement resolution: min(default, playbook).

    The playbook may tighten the suggestion below the conservative default but
    never raise it above. Returns (suggested_cagr, suggestion_source).
    """
    default = DEFAULT_CAP[path]
    if playbook_growth_ceiling is not None:
        suggested = min(default, playbook_growth_ceiling)
        source = "playbook_ceiling" if playbook_growth_ceiling < default else "default_cap"
    else:
        suggested = default
        source = "default_cap"
    return suggested, source


def apply_confidence_cap(prior_confidence, flag):
    """Confirmed trip caps meta.confidence at MEDIUM. One-way; never raises."""
    if not (flag.get("tripped") and flag.get("operator_confirmed")):
        return prior_confidence
    rank = CONFIDENCE_ORDER[prior_confidence]
    return "MEDIUM" if rank > CONFIDENCE_ORDER["MEDIUM"] else prior_confidence


# ---------------------------------------------------------------------------
# Contract validators
# ---------------------------------------------------------------------------

def validate_base_year_flag(block):
    """Raise AssertionError if `block` violates the documented contract.

    Mirrors SKILL.md §"Top-level meta.base_year_flag (ABA-134)".
    """
    assert isinstance(block, dict), "base_year_flag must be an object"

    tripped = block.get("tripped")
    assert isinstance(tripped, bool), "tripped must be bool"

    assert block.get("tripwire") in TRIPWIRE_ENUM, f"tripwire {block.get('tripwire')!r} not in enum"
    assert block.get("suggestion_source") in SUGGESTION_SOURCE_ENUM, (
        f"suggestion_source {block.get('suggestion_source')!r} not in enum"
    )

    # original_cagr_3y and base_year_ratio are populated every run (audit symmetry).
    assert isinstance(block.get("original_cagr_3y"), (int, float)), (
        "original_cagr_3y must be numeric every run"
    )
    assert isinstance(block.get("base_year_ratio"), (int, float)), (
        "base_year_ratio must be numeric every run"
    )

    cca = block.get("confidence_cap_applied")
    assert cca in ("MEDIUM", None), "confidence_cap_applied must be 'MEDIUM' or null"

    if not tripped:
        # No-trip: every trip-specific field is null.
        for f in ("tripwire", "suggested_cagr", "suggestion_source",
                  "operator_confirmed", "confidence_cap_applied"):
            assert block.get(f) is None, f"not-tripped block must null {f}"
        return

    # tripped == True
    assert block.get("tripwire") is not None, "tripped block must name a tripwire"
    assert isinstance(block.get("suggested_cagr"), (int, float)), (
        "tripped block must compute suggested_cagr"
    )
    assert 0 < block["suggested_cagr"] <= 1.0, "suggested_cagr out of sane range"
    assert block.get("suggestion_source") in {"playbook_ceiling", "default_cap", "operator_override"}, (
        "tripped block must name a non-null suggestion_source"
    )

    confirmed = block.get("operator_confirmed")
    assert isinstance(confirmed, bool), "operator_confirmed must be bool when tripped"

    if confirmed:
        assert cca == "MEDIUM", "confirmed trip caps confidence at MEDIUM"
    else:
        # Declined / non-interactive: the run halted, no IV was produced, so no
        # confidence cap is recorded — and the operator never engaged, so the
        # suggestion cannot have come from an override.
        assert cca is None, "declined trip produced no IV — confidence_cap_applied must be null"
        assert block["suggestion_source"] != "operator_override", (
            "operator_override implies the operator engaged — inconsistent with "
            "operator_confirmed=False"
        )


def validate_y2_5_cagr_source(source, flag):
    """Cross-block: each scenario's y2_5_cagr_source must agree with the flag.

    Only called when scenarios exist — i.e. not on a declined/halted trip.
    """
    assert source in Y2_5_CAGR_SOURCE_ENUM, f"y2_5_cagr_source {source!r} not in enum"

    if not flag["tripped"]:
        assert source == "mechanical", "no-trip run must tag scenarios 'mechanical'"
        return

    assert flag.get("operator_confirmed") is True, (
        "scenarios should not exist on a declined/halted trip"
    )
    ss = flag["suggestion_source"]
    expected = {
        "operator_override": "operator_override",
        "playbook_ceiling": "playbook_ceiling",
        "default_cap": "operator_confirmed_cap",
    }[ss]
    assert source == expected, (
        f"y2_5_cagr_source {source!r} inconsistent with suggestion_source {ss!r}"
    )


# ---------------------------------------------------------------------------
# Detection — OR-composite and tripwire encoding
# ---------------------------------------------------------------------------

def test_nvda_established_trips_both_signals():
    # FY23 clean FCF base depressed: CAGR 194%, ratio ~0.012.
    tripped, tripwire = detect(1.94, 0.012, "established")
    assert tripped is True
    assert tripwire == "abs_cagr+ratio"


def test_nvda_pre_profit_trips_both_signals():
    # FY23 pre-AI revenue base: CAGR 100%, ratio 0.125 (27/216).
    tripped, tripwire = detect(1.00, 0.125, "pre_profit")
    assert tripped is True
    assert tripwire == "abs_cagr+ratio"


def test_d1_only_established():
    # High CAGR, healthy base (ratio above threshold).
    tripped, tripwire = detect(0.45, 0.40, "established")
    assert tripped is True
    assert tripwire == "abs_cagr_40"


def test_d1_only_pre_profit_uses_50_label():
    tripped, tripwire = detect(0.55, 0.40, "pre_profit")
    assert tripped is True
    assert tripwire == "abs_cagr_50"


def test_d2_only_depressed_base_with_modest_cagr():
    # Depressed base (ratio < 0.15) but CAGR below the absolute ceiling — e.g. a
    # one-off recovery year that doesn't compound to a huge CAGR.
    tripped, tripwire = detect(0.35, 0.10, "established")
    assert tripped is True
    assert tripwire == "base_year_ratio_15"


def test_no_trip_healthy_grower():
    tripped, tripwire = detect(0.18, 0.61, "established")
    assert tripped is False
    assert tripwire is None


def test_negative_base_year_trips_d2():
    # A negative base-year clean FCF yields a negative ratio (< 0.15) and trips —
    # the most distorted base is exactly the one the guard must catch.
    tripped, tripwire = detect(2.5, -0.20, "established")
    assert tripped is True
    assert "ratio" in tripwire  # abs_cagr+ratio (D1 also fires)


# ---------------------------------------------------------------------------
# Threshold calibration — the ABA-104 reject-D5 table
# ---------------------------------------------------------------------------

def _ratio_for_sustained_cagr(g, years=3):
    """base/current for a CAGR g sustained over `years`: 1 / (1+g)**years."""
    return 1.0 / (1.0 + g) ** years


@pytest.mark.parametrize(
    "sustained_cagr,expect_d2_trip",
    [
        (0.30, False),   # ratio 0.455 — safe
        (0.40, False),   # ratio 0.364 — safe
        (0.50, False),   # ratio 0.296 — would false-trip at 0.30, safe at 0.15
        (0.60, False),   # ratio 0.244 — would false-trip at 0.30, safe at 0.15
        (0.85, False),   # ratio 0.158 — borderline, just above 0.15: no trip
    ],
)
def test_d2_does_not_false_trip_sustained_growth(sustained_cagr, expect_d2_trip):
    ratio = _ratio_for_sustained_cagr(sustained_cagr)
    d2 = ratio < D2_RATIO_THRESHOLD
    assert d2 is expect_d2_trip, (
        f"sustained {sustained_cagr:.0%} → ratio {ratio:.3f}; D2 trip={d2}"
    )


@pytest.mark.parametrize("ratio", [0.125, 0.039])
def test_d2_trips_genuinely_depressed_base(ratio):
    # NVDA revenue (0.125) and FCF (0.039) bases both fire D2.
    assert ratio < D2_RATIO_THRESHOLD


# ---------------------------------------------------------------------------
# Suggested replacement — min(default, playbook ceiling)
# ---------------------------------------------------------------------------

def test_nvda_established_suggestion_is_default_not_playbook():
    # Playbook growth_ceiling 0.35 > 0.25 default → default wins (AC #82).
    suggested, source = resolve_suggestion("established", playbook_growth_ceiling=0.35)
    assert suggested == 0.25
    assert source == "default_cap"


def test_nvda_pre_profit_suggestion_is_default():
    suggested, source = resolve_suggestion("pre_profit", playbook_growth_ceiling=0.35)
    assert suggested == 0.30
    assert source == "default_cap"


def test_playbook_can_tighten_below_default():
    # A slow-grower playbook ceiling below the default lowers the suggestion.
    suggested, source = resolve_suggestion("established", playbook_growth_ceiling=0.15)
    assert suggested == 0.15
    assert source == "playbook_ceiling"


def test_no_playbook_uses_default():
    suggested, source = resolve_suggestion("pre_profit")
    assert suggested == 0.30
    assert source == "default_cap"


# ---------------------------------------------------------------------------
# Artefact shape — base_year_flag contract
# ---------------------------------------------------------------------------

def _not_tripped_flag():
    return {
        "tripped": False,
        "tripwire": None,
        "original_cagr_3y": 0.18,
        "base_year_ratio": 0.61,
        "suggested_cagr": None,
        "suggestion_source": None,
        "operator_confirmed": None,
        "confidence_cap_applied": None,
    }


def _tripped_confirmed_flag():
    return {
        "tripped": True,
        "tripwire": "abs_cagr+ratio",
        "original_cagr_3y": 3.34,
        "base_year_ratio": 0.012,
        "suggested_cagr": 0.25,
        "suggestion_source": "default_cap",
        "operator_confirmed": True,
        "confidence_cap_applied": "MEDIUM",
    }


def _tripped_declined_flag():
    return {
        "tripped": True,
        "tripwire": "abs_cagr+ratio",
        "original_cagr_3y": 3.34,
        "base_year_ratio": 0.012,
        "suggested_cagr": 0.25,
        "suggestion_source": "default_cap",
        "operator_confirmed": False,
        "confidence_cap_applied": None,
    }


def test_not_tripped_shape_passes():
    validate_base_year_flag(_not_tripped_flag())


def test_tripped_confirmed_shape_passes():
    validate_base_year_flag(_tripped_confirmed_flag())


def test_tripped_confirmed_override_shape_passes():
    block = _tripped_confirmed_flag()
    block["suggested_cagr"] = 0.20
    block["suggestion_source"] = "operator_override"
    validate_base_year_flag(block)


def test_tripped_declined_shape_passes():
    validate_base_year_flag(_tripped_declined_flag())


def test_not_tripped_with_tripwire_rejected():
    block = _not_tripped_flag()
    block["tripwire"] = "abs_cagr_40"
    with pytest.raises(AssertionError, match="must null tripwire"):
        validate_base_year_flag(block)


def test_tripped_without_suggested_cagr_rejected():
    block = _tripped_confirmed_flag()
    block["suggested_cagr"] = None
    with pytest.raises(AssertionError, match="must compute suggested_cagr"):
        validate_base_year_flag(block)


def test_confirmed_without_medium_cap_rejected():
    block = _tripped_confirmed_flag()
    block["confidence_cap_applied"] = None
    with pytest.raises(AssertionError, match="caps confidence at MEDIUM"):
        validate_base_year_flag(block)


def test_declined_with_medium_cap_rejected():
    block = _tripped_declined_flag()
    block["confidence_cap_applied"] = "MEDIUM"
    with pytest.raises(AssertionError, match="must be null"):
        validate_base_year_flag(block)


def test_declined_with_override_source_rejected():
    block = _tripped_declined_flag()
    block["suggestion_source"] = "operator_override"
    with pytest.raises(AssertionError, match="operator_override implies"):
        validate_base_year_flag(block)


def test_original_cagr_required_even_when_not_tripped():
    block = _not_tripped_flag()
    block["original_cagr_3y"] = None
    with pytest.raises(AssertionError, match="original_cagr_3y must be numeric"):
        validate_base_year_flag(block)


# ---------------------------------------------------------------------------
# y2_5_cagr_source — enum + consistency with the flag
# ---------------------------------------------------------------------------

def test_y2_5_source_mechanical_when_not_tripped():
    validate_y2_5_cagr_source("mechanical", _not_tripped_flag())


def test_y2_5_source_confirmed_cap_maps_from_default():
    validate_y2_5_cagr_source("operator_confirmed_cap", _tripped_confirmed_flag())


def test_y2_5_source_playbook_maps_from_playbook_suggestion():
    flag = _tripped_confirmed_flag()
    flag["suggestion_source"] = "playbook_ceiling"
    flag["suggested_cagr"] = 0.15
    validate_y2_5_cagr_source("playbook_ceiling", flag)


def test_y2_5_source_override_maps_from_override():
    flag = _tripped_confirmed_flag()
    flag["suggestion_source"] = "operator_override"
    flag["suggested_cagr"] = 0.20
    validate_y2_5_cagr_source("operator_override", flag)


def test_y2_5_source_mismatch_rejected():
    # default_cap suggestion must map to operator_confirmed_cap, not playbook_ceiling.
    with pytest.raises(AssertionError, match="inconsistent with suggestion_source"):
        validate_y2_5_cagr_source("playbook_ceiling", _tripped_confirmed_flag())


def test_y2_5_source_mechanical_on_trip_rejected():
    with pytest.raises(AssertionError):
        validate_y2_5_cagr_source("mechanical", _tripped_confirmed_flag())


# ---------------------------------------------------------------------------
# Confidence cap — one-way to MEDIUM on confirmed trip
# ---------------------------------------------------------------------------

def test_confirmed_trip_caps_high_to_medium():
    assert apply_confidence_cap("HIGH", _tripped_confirmed_flag()) == "MEDIUM"


def test_confirmed_trip_leaves_medium_unchanged():
    assert apply_confidence_cap("MEDIUM", _tripped_confirmed_flag()) == "MEDIUM"


def test_confirmed_trip_never_raises_low():
    assert apply_confidence_cap("LOW", _tripped_confirmed_flag()) == "LOW"


def test_no_trip_is_pass_through():
    assert apply_confidence_cap("HIGH", _not_tripped_flag()) == "HIGH"


def test_declined_trip_is_pass_through():
    # Declined run halts before an IV — confidence cap is moot, pass-through here.
    assert apply_confidence_cap("HIGH", _tripped_declined_flag()) == "HIGH"
