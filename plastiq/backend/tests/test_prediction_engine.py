"""
Unit tests for app.services.prediction_engine.

Run with:
    pytest tests/test_prediction_engine.py -v

These tests do NOT require FastAPI, SQLAlchemy, or a database — the engine
is pure functions over dataclasses by design, so it can be verified in
complete isolation.
"""

import pytest

from app.ml.polymer_reference import PlasticType, Suitability
from app.services.prediction_engine import (
    CompositionItem,
    build_prediction_report,
    estimate_feedstock,
    predict_revenue,
    predict_yield,
)


def make_spec_example_composition():
    """Reproduces the worked example from the system spec exactly:
    Total Waste = 10 Tons. HDPE=2.1, LDPE=1.8, PP=1.5 (suitable), PVC=0.8
    (rejected), PET=3.8 (rejected) to make the total exactly 10 tons.
    """
    return [
        CompositionItem(PlasticType.HDPE, 2.1, avg_confidence=0.95),
        CompositionItem(PlasticType.LDPE, 1.8, avg_confidence=0.95),
        CompositionItem(PlasticType.PP, 1.5, avg_confidence=0.95),
        CompositionItem(PlasticType.PVC, 0.8, avg_confidence=0.95),
        CompositionItem(PlasticType.PET, 3.8, avg_confidence=0.95),
    ]


class TestSuitability:
    def test_pvc_is_rejected(self):
        report = build_prediction_report(make_spec_example_composition())
        pvc_line = next(l for l in report.suitability_lines if l.plastic_type == PlasticType.PVC)
        assert pvc_line.suitability == Suitability.POOR_HAZARDOUS
        assert pvc_line.included_in_feedstock is False

    def test_hdpe_ldpe_pp_are_highly_suitable(self):
        report = build_prediction_report(make_spec_example_composition())
        for ptype in (PlasticType.HDPE, PlasticType.LDPE, PlasticType.PP):
            line = next(l for l in report.suitability_lines if l.plastic_type == ptype)
            assert line.suitability == Suitability.HIGHLY_SUITABLE
            assert line.included_in_feedstock is True


class TestFeedstockEstimation:
    def test_matches_spec_worked_example(self):
        """Spec: Total Suitable Feedstock = 5.4 Tons (2.1 + 1.8 + 1.5)."""
        report = build_prediction_report(make_spec_example_composition())
        assert report.suitable_feedstock_tons == pytest.approx(5.4, abs=0.001)
        assert report.total_waste_tons == pytest.approx(10.0, abs=0.001)

    def test_pvc_contamination_pct(self):
        """0.8 t PVC out of 10 t total = 8% contamination, matching the spec."""
        report = build_prediction_report(make_spec_example_composition())
        assert report.contamination_pct == pytest.approx(8.0, abs=0.01)


class TestYieldPrediction:
    def test_matches_spec_worked_example(self):
        """
        Spec: HDPE 2.1t x 80% = 1.68t oil; LDPE 1.8t x 85% = 1.53t oil;
        PP 1.5t x 75% = 1.125t oil (spec rounds display to 1.13t).
        Total estimated oil = 4.34t (spec) / 4.335t (unrounded exact).
        """
        report = build_prediction_report(make_spec_example_composition())
        oil_by_type = {l.plastic_type: l.oil_tons for l in report.yield_summary.lines}

        assert oil_by_type[PlasticType.HDPE] == pytest.approx(1.68, abs=0.001)
        assert oil_by_type[PlasticType.LDPE] == pytest.approx(1.53, abs=0.001)
        assert oil_by_type[PlasticType.PP] == pytest.approx(1.125, abs=0.001)
        assert report.yield_summary.total_oil_tons == pytest.approx(4.335, abs=0.001)

    def test_pvc_contributes_zero_yield(self):
        report = build_prediction_report(make_spec_example_composition())
        pvc_in_yield_lines = [l for l in report.yield_summary.lines if l.plastic_type == PlasticType.PVC]
        assert pvc_in_yield_lines == []  # excluded entirely, not just zeroed


class TestRevenuePrediction:
    def test_oil_revenue_matches_spec_at_default_price(self):
        """Spec: 4.34 tons oil x $600/ton = $2,604. We get 4.335 x 600 = $2601."""
        report = build_prediction_report(make_spec_example_composition())
        oil_revenue = next(l for l in report.revenue_summary.lines if l.product == "Pyrolysis Oil")
        assert oil_revenue.revenue_usd == pytest.approx(2601.0, abs=1.0)

    def test_custom_pricing_is_respected(self):
        report = build_prediction_report(
            make_spec_example_composition(),
            pricing={"pyrolysis_oil_usd_per_ton": 700.0},
        )
        oil_revenue = next(l for l in report.revenue_summary.lines if l.product == "Pyrolysis Oil")
        assert oil_revenue.price_usd_per_ton == 700.0
        assert oil_revenue.revenue_usd == pytest.approx(4.335 * 700.0, abs=0.01)


class TestRiskDetection:
    def test_high_pvc_contamination_flags_critical_risk(self):
        report = build_prediction_report(make_spec_example_composition())
        critical_codes = [r.code for r in report.risks if r.severity == "CRITICAL"]
        assert "PVC_CONTAMINATION_CRITICAL" in critical_codes

    def test_no_pvc_means_no_contamination_risk(self):
        composition = [CompositionItem(PlasticType.HDPE, 5.0, avg_confidence=0.95)]
        report = build_prediction_report(composition)
        codes = [r.code for r in report.risks]
        assert "PVC_CONTAMINATION_CRITICAL" not in codes
        assert "PVC_CONTAMINATION_WARNING" not in codes

    def test_high_machine_utilization_flags_warning(self):
        composition = [CompositionItem(PlasticType.HDPE, 5.0, avg_confidence=0.95)]
        report = build_prediction_report(composition, machine_utilization_pct=95.0)
        codes = [r.code for r in report.risks]
        assert "MACHINE_UTILIZATION_HIGH" in codes


class TestRecommendations:
    def test_pvc_removal_recommended_when_present(self):
        report = build_prediction_report(make_spec_example_composition())
        actions = [r.action for r in report.recommendations]
        assert any("Remove PVC" in a for a in actions)

    def test_no_recommendations_list_is_never_empty(self):
        composition = [CompositionItem(PlasticType.HDPE, 5.0, avg_confidence=0.95)]
        report = build_prediction_report(composition)
        assert len(report.recommendations) >= 1


class TestEdgeCases:
    def test_empty_composition_does_not_crash(self):
        report = build_prediction_report([])
        assert report.total_waste_tons == 0
        assert report.suitable_feedstock_tons == 0
        assert report.yield_summary.total_oil_tons == 0
        assert report.revenue_summary.total_revenue_usd == 0

    def test_all_pvc_results_in_zero_feedstock(self):
        composition = [CompositionItem(PlasticType.PVC, 10.0, avg_confidence=0.95)]
        report = build_prediction_report(composition)
        assert report.suitable_feedstock_tons == 0
        assert report.contamination_pct == pytest.approx(100.0, abs=0.01)

    def test_mixed_plastics_use_moderate_yield_profile(self):
        composition = [CompositionItem(PlasticType.MIXED, 4.0, avg_confidence=0.7)]
        report = build_prediction_report(composition)
        assert report.suitable_feedstock_tons == pytest.approx(4.0, abs=0.001)
        assert report.yield_summary.total_oil_tons == pytest.approx(4.0 * 0.55, abs=0.001)
