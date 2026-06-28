"""
Core Pyrolysis Prediction Engine.

Implements Steps 3-7 of the workflow spec:
  3. Determine pyrolysis suitability
  4. Estimate available (suitable) feedstock
  5. Predict pyrolysis output (oil yield)
  6. Predict other outputs (gas, carbon black, wax)
  7. Revenue prediction

Plus risk detection and recommendation generation, adapted from the generic
RISK DETECTION RULES / OPTIMIZATION RULES / AI RESPONSE FORMAT sections of the
secondary reference document.

Design goal: this module is pure functions over plain dataclasses — no DB,
no FastAPI — so it can be unit tested in complete isolation (see
tests/test_engine.py) and reused from batch jobs, the API, or a notebook.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.ml.polymer_reference import (
    DEFAULT_PRICING,
    POLYMER_PROFILE,
    RISK_THRESHOLDS,
    PlasticType,
    Suitability,
)


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class CompositionItem:
    plastic_type: PlasticType
    weight_tons: float
    avg_confidence: float = 1.0
    item_count: int = 0


@dataclass
class SuitabilityLine:
    plastic_type: PlasticType
    weight_tons: float
    suitability: Suitability
    reason: str
    included_in_feedstock: bool
    contamination_pct_of_total: float


@dataclass
class YieldLine:
    plastic_type: PlasticType
    input_tons: float
    oil_tons: float
    gas_tons: float
    char_tons: float
    wax_tons: float


@dataclass
class YieldSummary:
    total_input_tons: float
    total_oil_tons: float
    total_gas_tons: float
    total_char_tons: float
    total_wax_tons: float
    lines: List[YieldLine]

    @property
    def overall_oil_yield_pct(self) -> float:
        if self.total_input_tons <= 0:
            return 0.0
        return round((self.total_oil_tons / self.total_input_tons) * 100, 2)


@dataclass
class RevenueLine:
    product: str
    quantity_tons: float
    price_usd_per_ton: float
    revenue_usd: float


@dataclass
class RevenueSummary:
    lines: List[RevenueLine]
    total_revenue_usd: float


@dataclass
class RiskFlag:
    severity: str  # "INFO" | "WARNING" | "CRITICAL"
    code: str
    message: str


@dataclass
class Recommendation:
    priority: str  # "LOW" | "MEDIUM" | "HIGH"
    action: str


@dataclass
class Assumption:
    field: str
    assumption: str
    confidence_pct: float


@dataclass
class PredictionReport:
    """The full AI_RESPONSE_FORMAT-style structured output for one batch/run."""
    total_waste_tons: float
    composition: List[CompositionItem]
    suitability_lines: List[SuitabilityLine]
    suitable_feedstock_tons: float
    rejected_tons: float
    contamination_pct: float
    yield_summary: YieldSummary
    revenue_summary: RevenueSummary
    risks: List[RiskFlag]
    recommendations: List[Recommendation]
    assumptions: List[Assumption] = field(default_factory=list)
    executive_summary: str = ""


# ---------------------------------------------------------------------------
# Step 3: Suitability
# ---------------------------------------------------------------------------

def assess_suitability(
    composition: List[CompositionItem],
    total_waste_tons: float,
) -> List[SuitabilityLine]:
    lines: List[SuitabilityLine] = []
    for item in composition:
        profile = POLYMER_PROFILE[item.plastic_type]
        suitability = profile["suitability"]
        contamination_pct = (
            round((item.weight_tons / total_waste_tons) * 100, 2)
            if total_waste_tons > 0 else 0.0
        )

        if suitability == Suitability.POOR_HAZARDOUS:
            included = False
            if item.plastic_type == PlasticType.PVC:
                reason = (
                    "PVC releases hydrogen chloride (HCl) gas on pyrolysis, "
                    "corroding reactor internals and contaminating oil output. "
                    "Excluded from feedstock — must be physically removed, not "
                    "merely down-weighted."
                )
            else:
                reason = (
                    f"{profile['label']} has poor oil yield and high char "
                    f"formation under pyrolysis; mechanical recycling is "
                    f"preferred. Excluded from feedstock."
                )
        elif suitability == Suitability.MODERATE:
            included = True
            reason = (
                f"{profile['label']} is moderately suitable. "
                + (profile["hazard_notes"] or "Usable with standard process controls.")
            )
        elif suitability == Suitability.HIGHLY_SUITABLE:
            included = True
            reason = f"{profile['label']} is highly suitable for pyrolysis."
        else:
            included = False
            reason = "Unidentified or low-confidence material; excluded from feedstock pending manual review."

        lines.append(
            SuitabilityLine(
                plastic_type=item.plastic_type,
                weight_tons=item.weight_tons,
                suitability=suitability,
                reason=reason,
                included_in_feedstock=included,
                contamination_pct_of_total=contamination_pct,
            )
        )
    return lines


# ---------------------------------------------------------------------------
# Step 4: Feedstock estimation
# ---------------------------------------------------------------------------

def estimate_feedstock(suitability_lines: List[SuitabilityLine]) -> Dict[str, float]:
    suitable = sum(l.weight_tons for l in suitability_lines if l.included_in_feedstock)
    rejected = sum(l.weight_tons for l in suitability_lines if not l.included_in_feedstock)
    pvc_tons = sum(
        l.weight_tons for l in suitability_lines if l.plastic_type == PlasticType.PVC
    )
    total = suitable + rejected
    contamination_pct = round((pvc_tons / total) * 100, 2) if total > 0 else 0.0
    return {
        "suitable_feedstock_tons": round(suitable, 3),
        "rejected_tons": round(rejected, 3),
        "pvc_contamination_pct": contamination_pct,
    }


# ---------------------------------------------------------------------------
# Steps 5 & 6: Yield prediction (oil, gas, char, wax)
# ---------------------------------------------------------------------------

def predict_yield(
    suitability_lines: List[SuitabilityLine],
    yield_overrides: Optional[Dict[PlasticType, Dict[str, float]]] = None,
) -> YieldSummary:
    """
    yield_overrides lets a calibrated, plant-specific yield model (trained on
    this plant's pyrolysis_runs history — see services/calibration.py)
    override the default literature-based POLYMER_PROFILE coefficients.
    """
    overrides = yield_overrides or {}
    lines: List[YieldLine] = []

    for sl in suitability_lines:
        if not sl.included_in_feedstock or sl.weight_tons <= 0:
            continue
        profile = POLYMER_PROFILE[sl.plastic_type]
        coeffs = overrides.get(sl.plastic_type, profile)

        oil = sl.weight_tons * coeffs.get("oil_yield", profile["oil_yield"])
        gas = sl.weight_tons * coeffs.get("gas_yield", profile["gas_yield"])
        char = sl.weight_tons * coeffs.get("char_yield", profile["char_yield"])
        wax = sl.weight_tons * coeffs.get("wax_yield", profile["wax_yield"])

        lines.append(
            YieldLine(
                plastic_type=sl.plastic_type,
                input_tons=round(sl.weight_tons, 3),
                oil_tons=round(oil, 3),
                gas_tons=round(gas, 3),
                char_tons=round(char, 3),
                wax_tons=round(wax, 3),
            )
        )

    return YieldSummary(
        total_input_tons=round(sum(l.input_tons for l in lines), 3),
        total_oil_tons=round(sum(l.oil_tons for l in lines), 3),
        total_gas_tons=round(sum(l.gas_tons for l in lines), 3),
        total_char_tons=round(sum(l.char_tons for l in lines), 3),
        total_wax_tons=round(sum(l.wax_tons for l in lines), 3),
        lines=lines,
    )


# ---------------------------------------------------------------------------
# Step 7: Revenue prediction
# ---------------------------------------------------------------------------

def predict_revenue(
    yield_summary: YieldSummary,
    pricing: Optional[Dict[str, float]] = None,
) -> RevenueSummary:
    p = {**DEFAULT_PRICING, **(pricing or {})}

    lines = [
        RevenueLine(
            product="Pyrolysis Oil",
            quantity_tons=yield_summary.total_oil_tons,
            price_usd_per_ton=p["pyrolysis_oil_usd_per_ton"],
            revenue_usd=round(yield_summary.total_oil_tons * p["pyrolysis_oil_usd_per_ton"], 2),
        ),
        RevenueLine(
            product="Carbon Black",
            quantity_tons=yield_summary.total_char_tons,
            price_usd_per_ton=p["carbon_black_usd_per_ton"],
            revenue_usd=round(yield_summary.total_char_tons * p["carbon_black_usd_per_ton"], 2),
        ),
        RevenueLine(
            product="Wax Residue",
            quantity_tons=yield_summary.total_wax_tons,
            price_usd_per_ton=p["wax_usd_per_ton"],
            revenue_usd=round(yield_summary.total_wax_tons * p["wax_usd_per_ton"], 2),
        ),
        RevenueLine(
            product="Pyrolysis Gas",
            quantity_tons=yield_summary.total_gas_tons,
            price_usd_per_ton=p["pyrolysis_gas_usd_per_ton"],
            revenue_usd=round(yield_summary.total_gas_tons * p["pyrolysis_gas_usd_per_ton"], 2),
        ),
    ]
    total = round(sum(l.revenue_usd for l in lines), 2)
    return RevenueSummary(lines=lines, total_revenue_usd=total)


# ---------------------------------------------------------------------------
# Risk detection (adapted from RISK DETECTION RULES)
# ---------------------------------------------------------------------------

def detect_risks(
    feedstock: Dict[str, float],
    yield_summary: YieldSummary,
    suitability_lines: List[SuitabilityLine],
    machine_utilization_pct: Optional[float] = None,
    target_profit_margin_pct: Optional[float] = None,
    actual_profit_margin_pct: Optional[float] = None,
) -> List[RiskFlag]:
    risks: List[RiskFlag] = []
    pvc_pct = feedstock.get("pvc_contamination_pct", 0.0)

    if pvc_pct >= RISK_THRESHOLDS["pvc_contamination_pct_critical"]:
        risks.append(RiskFlag(
            severity="CRITICAL",
            code="PVC_CONTAMINATION_CRITICAL",
            message=(
                f"PVC contamination is {pvc_pct}% of total waste — above the "
                f"{RISK_THRESHOLDS['pvc_contamination_pct_critical']}% critical "
                f"threshold. Halt feedstock loading until PVC is sorted out; "
                f"risk of HCl corrosion and oil contamination is high."
            ),
        ))
    elif pvc_pct >= RISK_THRESHOLDS["pvc_contamination_pct_warning"]:
        risks.append(RiskFlag(
            severity="WARNING",
            code="PVC_CONTAMINATION_WARNING",
            message=(
                f"PVC contamination is {pvc_pct}% — above the "
                f"{RISK_THRESHOLDS['pvc_contamination_pct_warning']}% warning "
                f"threshold. Recommend additional sorting pass."
            ),
        ))

    if feedstock.get("suitable_feedstock_tons", 0.0) < RISK_THRESHOLDS["safety_stock_feedstock_tons"]:
        risks.append(RiskFlag(
            severity="WARNING",
            code="FEEDSTOCK_BELOW_SAFETY_STOCK",
            message=(
                f"Suitable feedstock ({feedstock.get('suitable_feedstock_tons', 0.0)} t) "
                f"is below the safety stock threshold of "
                f"{RISK_THRESHOLDS['safety_stock_feedstock_tons']} t. A production run "
                f"may not be economically viable without additional intake."
            ),
        ))

    if machine_utilization_pct is not None and machine_utilization_pct >= RISK_THRESHOLDS["machine_utilization_pct_warning"]:
        risks.append(RiskFlag(
            severity="WARNING",
            code="MACHINE_UTILIZATION_HIGH",
            message=(
                f"Reactor utilization is projected at {machine_utilization_pct}%, "
                f"above the {RISK_THRESHOLDS['machine_utilization_pct_warning']}% "
                f"threshold. Elevated downtime/maintenance risk — consider "
                f"scheduling a maintenance window before next run."
            ),
        ))

    if actual_profit_margin_pct is not None:
        target = target_profit_margin_pct or RISK_THRESHOLDS["min_target_profit_margin_pct"]
        if actual_profit_margin_pct < target:
            risks.append(RiskFlag(
                severity="WARNING",
                code="PROFIT_MARGIN_BELOW_TARGET",
                message=(
                    f"Projected profit margin ({actual_profit_margin_pct}%) is "
                    f"below the target of {target}%."
                ),
            ))

    low_conf_types = [
        sl.plastic_type for sl in suitability_lines
        if sl.suitability == Suitability.UNKNOWN
    ]
    if low_conf_types:
        risks.append(RiskFlag(
            severity="INFO",
            code="LOW_CONFIDENCE_DETECTIONS",
            message=(
                f"{len(low_conf_types)} material group(s) could not be confidently "
                f"classified and were excluded from feedstock pending manual review."
            ),
        ))

    return risks


# ---------------------------------------------------------------------------
# Recommendations (adapted from OPTIMIZATION RULES)
# ---------------------------------------------------------------------------

def generate_recommendations(
    feedstock: Dict[str, float],
    suitability_lines: List[SuitabilityLine],
    yield_summary: YieldSummary,
    risks: List[RiskFlag],
) -> List[Recommendation]:
    recs: List[Recommendation] = []

    pvc_pct = feedstock.get("pvc_contamination_pct", 0.0)
    if pvc_pct > 0:
        priority = "HIGH" if pvc_pct >= RISK_THRESHOLDS["pvc_contamination_pct_warning"] else "MEDIUM"
        recs.append(Recommendation(
            priority=priority,
            action=f"Remove PVC before processing — currently {pvc_pct}% of incoming stream.",
        ))

    ps_lines = [l for l in suitability_lines if l.plastic_type == PlasticType.PS and l.included_in_feedstock]
    if ps_lines and sum(l.weight_tons for l in ps_lines) > 0:
        recs.append(Recommendation(
            priority="LOW",
            action="PS detected — ensure vapor capture/scrubbing is active to manage styrene off-gassing.",
        ))

    pet_rejected = [l for l in suitability_lines if l.plastic_type == PlasticType.PET and not l.included_in_feedstock]
    if pet_rejected and sum(l.weight_tons for l in pet_rejected) > 0.5:
        recs.append(Recommendation(
            priority="MEDIUM",
            action=(
                f"{round(sum(l.weight_tons for l in pet_rejected), 2)} t of PET detected — "
                f"route to mechanical/bottle-to-bottle recycling stream rather than pyrolysis "
                f"for better economic and environmental return."
            ),
        ))

    if feedstock.get("suitable_feedstock_tons", 0.0) >= RISK_THRESHOLDS["safety_stock_feedstock_tons"]:
        recs.append(Recommendation(
            priority="LOW",
            action=(
                f"{feedstock['suitable_feedstock_tons']} t of suitable feedstock is ready — "
                f"production run is feasible."
            ),
        ))

    if any(r.code == "MACHINE_UTILIZATION_HIGH" for r in risks):
        recs.append(Recommendation(
            priority="MEDIUM",
            action="Schedule preventive maintenance window — reactor utilization trending high.",
        ))

    if not recs:
        recs.append(Recommendation(
            priority="LOW",
            action="No immediate optimization actions identified for this batch.",
        ))

    return recs


# ---------------------------------------------------------------------------
# Orchestration: builds the full AI_RESPONSE_FORMAT-style report
# ---------------------------------------------------------------------------

def build_prediction_report(
    composition: List[CompositionItem],
    pricing: Optional[Dict[str, float]] = None,
    yield_overrides: Optional[Dict[PlasticType, Dict[str, float]]] = None,
    machine_utilization_pct: Optional[float] = None,
    target_profit_margin_pct: Optional[float] = None,
    processing_cost_usd_per_ton: Optional[float] = None,
) -> PredictionReport:
    total_waste = round(sum(c.weight_tons for c in composition), 3)

    suitability_lines = assess_suitability(composition, total_waste)
    feedstock = estimate_feedstock(suitability_lines)
    yield_summary = predict_yield(suitability_lines, yield_overrides)
    revenue_summary = predict_revenue(yield_summary, pricing)

    actual_margin_pct = None
    if processing_cost_usd_per_ton is not None and feedstock["suitable_feedstock_tons"] > 0:
        total_cost = processing_cost_usd_per_ton * feedstock["suitable_feedstock_tons"]
        if revenue_summary.total_revenue_usd > 0:
            actual_margin_pct = round(
                ((revenue_summary.total_revenue_usd - total_cost) / revenue_summary.total_revenue_usd) * 100, 2
            )

    risks = detect_risks(
        feedstock, yield_summary, suitability_lines,
        machine_utilization_pct=machine_utilization_pct,
        target_profit_margin_pct=target_profit_margin_pct,
        actual_profit_margin_pct=actual_margin_pct,
    )
    recommendations = generate_recommendations(feedstock, suitability_lines, yield_summary, risks)

    assumptions: List[Assumption] = []
    low_conf_items = [c for c in composition if c.avg_confidence < 0.6]
    for item in low_conf_items:
        assumptions.append(Assumption(
            field=f"{item.plastic_type.value} classification",
            assumption=(
                f"Average detection confidence was {round(item.avg_confidence * 100, 1)}%, "
                f"below the 60% reliability threshold — weight figure should be treated "
                f"as a low-confidence estimate."
            ),
            confidence_pct=round(item.avg_confidence * 100, 1),
        ))

    critical = sum(1 for r in risks if r.severity == "CRITICAL")
    warning = sum(1 for r in risks if r.severity == "WARNING")
    exec_summary = (
        f"Current waste stream contains {feedstock['suitable_feedstock_tons']} tons of "
        f"suitable pyrolysis feedstock out of {total_waste} tons received "
        f"({feedstock['rejected_tons']} t rejected). Estimated oil production is "
        f"{yield_summary.total_oil_tons} tons, with projected revenue of "
        f"${revenue_summary.total_revenue_usd:,.2f} across all output streams. "
        f"PVC contamination is {feedstock['pvc_contamination_pct']}%"
        + ("; remove PVC before processing." if feedstock['pvc_contamination_pct'] > 0 else ".")
        + (f" {critical} critical and {warning} warning risk(s) flagged." if (critical or warning) else " No risks flagged.")
    )

    return PredictionReport(
        total_waste_tons=total_waste,
        composition=composition,
        suitability_lines=suitability_lines,
        suitable_feedstock_tons=feedstock["suitable_feedstock_tons"],
        rejected_tons=feedstock["rejected_tons"],
        contamination_pct=feedstock["pvc_contamination_pct"],
        yield_summary=yield_summary,
        revenue_summary=revenue_summary,
        risks=risks,
        recommendations=recommendations,
        assumptions=assumptions,
        executive_summary=exec_summary,
    )
