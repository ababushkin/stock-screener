"""Audit-trail JSON shape tests for `stages.model.engagement_modifier` (ABA-66).

Covers:

- **NFR3** — JSON contract: applied entries populate all fields; non-applied
  entries set `status_reason` from the documented enum (or `null` when the
  status itself disambiguates, e.g. `no_kpi_mapping`).
- **NFR4** — Output cap: an applied modifier's base-scenario IV impact is
  bounded by ≤5%. When the pre-clamp impact would exceed 5%, `clamped_from`
  records the pre-clamp multiplier and `base_anchor_multiplier` records the
  clamped value.
- **NFR5** — Confidence cap: any run with `status: "applied"` caps
  `meta.confidence` at MEDIUM (one-way; never raises).
- **ADR D5** — Every emitted block records `kpi_map_schema_version`, even on
  non-applied statuses, so replays are reproducible against a known map state.

These are pure-data tests on the documented contract. They do not exercise the
live extraction pipeline — that's Task 12's golden-fixture remit.
"""
import math

import pytest


STATUS_ENUM = {
    "applied",
    "unavailable",
    "no_kpi_mapping",
    "user_skipped",
    "direction_disagreement",
}

STATUS_REASON_ENUM = {
    "missing_ai_layer",
    "no_recent_print",
    "source_unreachable",
    "extraction_failed",
    "non_interactive",
    None,
}

APPLIED_REQUIRED_FIELDS = (
    "status",
    "status_reason",
    "kpi_map_schema_version",
    "kpi_name",
    "kpi_value",
    "kpi_unit",
    "kpi_period",
    "yoy_change",
    "direction",
    "magnitude",
    "base_anchor_multiplier",
    "clamped_from",
    "revision",
    "agreement",
    "source_url",
    "user_confirmed",
)

CONFIDENCE_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


# ---------------------------------------------------------------------------
# Schema validator under test
# ---------------------------------------------------------------------------

def validate_engagement_modifier(block):
    """Raise AssertionError if `block` violates the documented contract.

    Mirrors SKILL.md §JSON contract for engagement_modifier (line ~496).
    """
    assert isinstance(block, dict), "engagement_modifier must be an object"

    status = block.get("status")
    assert status in STATUS_ENUM, f"status {status!r} not in enum"

    reason = block.get("status_reason")
    assert reason in STATUS_REASON_ENUM, f"status_reason {reason!r} not in enum"

    # ADR D5: schema version is always recorded.
    assert isinstance(block.get("kpi_map_schema_version"), int), (
        "kpi_map_schema_version must be an integer (ADR D5)"
    )

    if status == "applied":
        # NFR3: all applied-fields populated.
        # status_reason is always null in applied (per documented enum behaviour);
        # clamped_from is null when no clamp fired (FR4b);
        # agreement is null on legacy fall-through (Yahoo unreachable).
        nullable_in_applied = {"status_reason", "clamped_from", "agreement"}
        for f in APPLIED_REQUIRED_FIELDS:
            assert f in block, f"applied block missing field: {f}"
            if f in nullable_in_applied:
                continue
            assert block[f] is not None, f"applied field {f} must not be null"

        assert block["direction"] in (-1, 0, 1)
        assert block["magnitude"] in ("deadband", "mild", "strong")
        assert isinstance(block["base_anchor_multiplier"], (int, float))
        assert isinstance(block["user_confirmed"], bool)

        clamped = block["clamped_from"]
        assert clamped is None or isinstance(clamped, (int, float)), (
            "clamped_from must be null or numeric"
        )
        if clamped is not None:
            assert clamped != block["base_anchor_multiplier"], (
                "clamped_from is the *pre-clamp* multiplier; equal value means "
                "no clamp fired and it should be null"
            )

        rev = block["revision"]
        assert isinstance(rev, dict)
        assert rev.get("metric") == "eps_ntm_30d"
        # revision_pct / direction may be null on fetch failure (legacy fall-through);
        # the surrounding agreement field carries the null-flag semantics.
        assert rev.get("direction") in (-1, 0, 1, None)

        agreement = block["agreement"]
        assert agreement in (True, False, None)
        # agreement == False means direction_disagreement should have suppressed —
        # an applied block with agreement=False is a contract violation.
        assert agreement is not False, (
            "agreement=False in an applied block — guardrail should have "
            "suppressed to status=direction_disagreement"
        )
    else:
        # Non-applied: documented enum says status_reason carries the why,
        # except for no_kpi_mapping (enum doesn't cover "ticker not in map" — null).
        # All other non-applied fields are emitted as null per SKILL.md §522.
        if status == "no_kpi_mapping":
            assert reason is None
        elif status == "direction_disagreement":
            # Suppressed by guardrail; base_anchor_multiplier=1.00, clamped_from=null.
            assert block.get("base_anchor_multiplier") == 1.00
            assert block.get("clamped_from") is None
        elif status == "user_skipped":
            # Either user said no, or non-interactive runtime.
            assert reason in (None, "non_interactive")
        elif status == "unavailable":
            assert reason in {
                "missing_ai_layer",
                "no_recent_print",
                "source_unreachable",
                "extraction_failed",
            }


# ---------------------------------------------------------------------------
# NFR3 — contract shape fixtures
# ---------------------------------------------------------------------------

def _applied_meta_baseline():
    return {
        "status": "applied",
        "status_reason": None,
        "kpi_map_schema_version": 2,
        "kpi_name": "DAP",
        "kpi_value": 3.43,
        "kpi_unit": "billion",
        "kpi_period": "Q1 2026",
        "yoy_change": 0.054,
        "direction": 1,
        "magnitude": "mild",
        "base_anchor_multiplier": 1.02,
        "clamped_from": None,
        "revision": {
            "metric": "eps_ntm_30d",
            "revision_pct": 0.018,
            "direction": 1,
            "source_url": "https://finance.yahoo.com/quote/META/analysis/",
        },
        "agreement": True,
        "source_url": "https://www.sec.gov/Archives/edgar/data/1326801/.../ex991.htm",
        "user_confirmed": True,
    }


def test_applied_shape_passes_contract():
    validate_engagement_modifier(_applied_meta_baseline())


def test_applied_with_clamp_records_pre_clamp_value():
    block = _applied_meta_baseline()
    block["base_anchor_multiplier"] = 1.031   # clamped down
    block["clamped_from"] = 1.04              # original pre-clamp
    validate_engagement_modifier(block)


def test_applied_missing_field_rejected():
    block = _applied_meta_baseline()
    del block["kpi_name"]
    with pytest.raises(AssertionError, match="missing field: kpi_name"):
        validate_engagement_modifier(block)


def test_applied_with_null_field_rejected():
    block = _applied_meta_baseline()
    block["kpi_value"] = None
    with pytest.raises(AssertionError, match="kpi_value must not be null"):
        validate_engagement_modifier(block)


def test_applied_agreement_false_is_contract_violation():
    # Guardrail must have suppressed to direction_disagreement; an applied block
    # with agreement=False slipped through and is rejected.
    block = _applied_meta_baseline()
    block["agreement"] = False
    with pytest.raises(AssertionError, match="guardrail should have suppressed"):
        validate_engagement_modifier(block)


def test_clamped_from_equal_to_multiplier_is_contract_violation():
    block = _applied_meta_baseline()
    block["base_anchor_multiplier"] = 1.03
    block["clamped_from"] = 1.03   # nonsense — no clamp actually fired
    with pytest.raises(AssertionError, match="no clamp fired"):
        validate_engagement_modifier(block)


@pytest.mark.parametrize(
    "status,reason",
    [
        ("unavailable", "missing_ai_layer"),
        ("unavailable", "no_recent_print"),
        ("unavailable", "source_unreachable"),
        ("unavailable", "extraction_failed"),
        ("user_skipped", None),
        ("user_skipped", "non_interactive"),
        ("no_kpi_mapping", None),
    ],
)
def test_non_applied_shape_passes_contract(status, reason):
    block = {
        "status": status,
        "status_reason": reason,
        "kpi_map_schema_version": 2,
    }
    if status == "direction_disagreement":
        block["base_anchor_multiplier"] = 1.00
        block["clamped_from"] = None
    validate_engagement_modifier(block)


def test_direction_disagreement_shape():
    block = {
        "status": "direction_disagreement",
        "status_reason": None,
        "kpi_map_schema_version": 2,
        "base_anchor_multiplier": 1.00,
        "clamped_from": None,
    }
    validate_engagement_modifier(block)


def test_no_kpi_mapping_with_non_null_reason_rejected():
    block = {
        "status": "no_kpi_mapping",
        "status_reason": "missing_ai_layer",   # wrong — enum says null
        "kpi_map_schema_version": 2,
    }
    with pytest.raises(AssertionError):
        validate_engagement_modifier(block)


def test_kpi_map_schema_version_required_on_every_status():
    """ADR D5: schema version is recorded on every emitted block, even
    non-applied ones, so replays can reconstruct the map state at run time."""
    for status in STATUS_ENUM:
        block = {"status": status, "status_reason": None}
        if status == "no_kpi_mapping":
            block["status_reason"] = None
        elif status == "unavailable":
            block["status_reason"] = "source_unreachable"
        elif status == "direction_disagreement":
            block["base_anchor_multiplier"] = 1.00
            block["clamped_from"] = None
        # No kpi_map_schema_version → should fail.
        with pytest.raises(AssertionError, match="kpi_map_schema_version"):
            validate_engagement_modifier(block)


# ---------------------------------------------------------------------------
# NFR4 — output cap clamp behaviour
# ---------------------------------------------------------------------------

def apply_output_cap(base_anchor_multiplier, base_iv_modified, base_iv_unmodified,
                     cap=0.05, tol=1e-3, max_iter=50):
    """Mirrors COMPUTE Step 6b clamp logic.

    Returns (clamped_multiplier, clamped_from). When no clamp fires,
    clamped_from is None.
    """
    if base_iv_unmodified == 0:
        return base_anchor_multiplier, None

    iv_impact_pct = abs(base_iv_modified / base_iv_unmodified - 1)
    if iv_impact_pct <= cap:
        return base_anchor_multiplier, None

    # Linear DCF response approximation: iv_impact_pct scales ~linearly with
    # (multiplier - 1) for small perturbations. Bisect between 1.00 and the
    # original applied multiplier.
    lo, hi = 1.00, base_anchor_multiplier
    if hi < lo:
        lo, hi = hi, lo

    # Per-unit-of-multiplier IV impact (slope).
    slope = iv_impact_pct / abs(base_anchor_multiplier - 1.00)

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        impact_at_mid = slope * abs(mid - 1.00)
        if abs(impact_at_mid - cap) <= tol or abs(hi - lo) <= tol:
            return mid, base_anchor_multiplier
        if impact_at_mid > cap:
            if base_anchor_multiplier > 1.00:
                hi = mid
            else:
                lo = mid
        else:
            if base_anchor_multiplier > 1.00:
                lo = mid
            else:
                hi = mid

    return mid, base_anchor_multiplier


def test_cap_holds_no_clamp_when_impact_below_threshold():
    # +2% Y1 anchor, base IV swing also modest (linear-ish low-leverage DCF).
    m, clamped_from = apply_output_cap(
        base_anchor_multiplier=1.02,
        base_iv_modified=103.0,
        base_iv_unmodified=100.0,
    )
    assert m == 1.02
    assert clamped_from is None


def test_clamp_fires_when_dcf_leverage_amplifies_modifier():
    # +4% Y1 anchor produces >5% base-IV swing (high-leverage DCF).
    m, clamped_from = apply_output_cap(
        base_anchor_multiplier=1.04,
        base_iv_modified=108.0,
        base_iv_unmodified=100.0,
    )
    assert clamped_from == 1.04, "pre-clamp multiplier must be recorded"
    assert m < 1.04, "clamped multiplier must be strictly smaller in absolute terms"
    # Verify the clamped multiplier maps to ≤5% IV impact under the linear model.
    slope = 0.08 / 0.04   # 8% IV impact at +4% multiplier
    impact_at_clamped = slope * abs(m - 1.00)
    assert impact_at_clamped <= 0.05 + 1e-3


def test_clamp_symmetric_negative_direction():
    # -4% Y1 anchor, -8% base IV swing.
    m, clamped_from = apply_output_cap(
        base_anchor_multiplier=0.96,
        base_iv_modified=92.0,
        base_iv_unmodified=100.0,
    )
    assert clamped_from == 0.96
    assert m > 0.96
    slope = 0.08 / 0.04
    impact_at_clamped = slope * abs(m - 1.00)
    assert impact_at_clamped <= 0.05 + 1e-3


def test_no_clamp_when_multiplier_is_one():
    # Deadband / direction_disagreement path — no perturbation.
    m, clamped_from = apply_output_cap(
        base_anchor_multiplier=1.00,
        base_iv_modified=100.0,
        base_iv_unmodified=100.0,
    )
    assert m == 1.00
    assert clamped_from is None


# ---------------------------------------------------------------------------
# NFR5 — confidence cap
# ---------------------------------------------------------------------------

def apply_confidence_cap(prior_confidence, modifier_status):
    """SKILL.md §223: applied modifier caps meta.confidence at MEDIUM. One-way;
    never raises. Non-applied statuses are pass-through."""
    if modifier_status != "applied":
        return prior_confidence
    rank = CONFIDENCE_ORDER[prior_confidence]
    return "MEDIUM" if rank > CONFIDENCE_ORDER["MEDIUM"] else prior_confidence


def test_applied_caps_high_to_medium():
    assert apply_confidence_cap("HIGH", "applied") == "MEDIUM"


def test_applied_leaves_medium_unchanged():
    assert apply_confidence_cap("MEDIUM", "applied") == "MEDIUM"


def test_applied_never_raises_low():
    assert apply_confidence_cap("LOW", "applied") == "LOW"


@pytest.mark.parametrize(
    "status",
    ["unavailable", "no_kpi_mapping", "user_skipped", "direction_disagreement"],
)
def test_non_applied_is_pass_through(status):
    assert apply_confidence_cap("HIGH", status) == "HIGH"
    assert apply_confidence_cap("MEDIUM", status) == "MEDIUM"
    assert apply_confidence_cap("LOW", status) == "LOW"
