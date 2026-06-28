from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.report import PredictionReportRecord, RiskFlagRecord
from app.models.user import User
from app.models.waste import WasteBatch
from app.schemas.dashboard import DashboardOut, KPISnapshot, PlasticTypeBreakdown, TrendPoint

router = APIRouter(prefix="/dashboard", tags=["Dashboard & BI"])


@router.get("", response_model=DashboardOut)
def get_dashboard(
    facility_id: Optional[int] = None,
    limit: int = 30,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = db.query(PredictionReportRecord).join(WasteBatch, PredictionReportRecord.batch_id == WasteBatch.id)
    if facility_id:
        q = q.filter(WasteBatch.facility_id == facility_id)
    records = q.order_by(PredictionReportRecord.id.desc()).limit(limit).all()

    if not records:
        empty_kpi = KPISnapshot(
            period_label=f"Last {limit} reports",
            total_waste_scanned_tons=0, total_suitable_feedstock_tons=0,
            feedstock_utilization_pct=0, total_oil_produced_tons=0,
            overall_oil_yield_pct=0, total_revenue_usd=0,
            estimated_total_cost_usd=0, estimated_net_profit_usd=0,
            estimated_profit_margin_pct=0, avg_pvc_contamination_pct=0,
            open_critical_risks=0, open_warning_risks=0, batches_processed=0,
        )
        return DashboardOut(kpis=empty_kpi, plastic_breakdown=[], oil_yield_trend=[], revenue_trend=[])

    total_waste = sum(r.total_waste_tons for r in records)
    total_feedstock = sum(r.suitable_feedstock_tons for r in records)
    total_oil = sum(r.total_oil_tons for r in records)
    total_revenue = sum(r.total_revenue_usd for r in records)
    avg_pvc = sum(r.contamination_pct for r in records) / len(records)

    # Cost estimate: pull from facility AI settings if available, else fall back
    # to a generic processing cost so the dashboard never silently hides cost info.
    sample_batch = db.query(WasteBatch).filter(WasteBatch.id == records[0].batch_id).first()
    cost_per_ton = 150.0
    if sample_batch and sample_batch.facility and sample_batch.facility.ai_settings:
        cost_per_ton = sample_batch.facility.ai_settings.processing_cost_usd_per_ton

    total_cost = total_feedstock * cost_per_ton
    net_profit = total_revenue - total_cost
    margin_pct = round((net_profit / total_revenue) * 100, 2) if total_revenue > 0 else 0.0

    report_ids = [r.id for r in records]
    risk_counts = db.query(RiskFlagRecord).filter(RiskFlagRecord.report_id.in_(report_ids)).all()
    critical = sum(1 for r in risk_counts if r.severity == "CRITICAL")
    warning = sum(1 for r in risk_counts if r.severity == "WARNING")

    kpis = KPISnapshot(
        period_label=f"Last {len(records)} reports",
        total_waste_scanned_tons=round(total_waste, 3),
        total_suitable_feedstock_tons=round(total_feedstock, 3),
        feedstock_utilization_pct=round((total_feedstock / total_waste) * 100, 2) if total_waste else 0.0,
        total_oil_produced_tons=round(total_oil, 3),
        overall_oil_yield_pct=round((total_oil / total_waste) * 100, 2) if total_waste else 0.0,
        total_revenue_usd=round(total_revenue, 2),
        estimated_total_cost_usd=round(total_cost, 2),
        estimated_net_profit_usd=round(net_profit, 2),
        estimated_profit_margin_pct=margin_pct,
        avg_pvc_contamination_pct=round(avg_pvc, 2),
        open_critical_risks=critical,
        open_warning_risks=warning,
        batches_processed=len(records),
    )

    # Plastic breakdown across all composition_json in window
    breakdown_agg: dict[str, float] = {}
    for r in records:
        for c in (r.composition_json or []):
            breakdown_agg[c["plastic_type"]] = breakdown_agg.get(c["plastic_type"], 0.0) + c["weight_tons"]
    total_breakdown = sum(breakdown_agg.values()) or 1.0
    plastic_breakdown = [
        PlasticTypeBreakdown(
            plastic_type=ptype,
            total_weight_tons=round(w, 3),
            pct_of_total=round((w / total_breakdown) * 100, 2),
        )
        for ptype, w in sorted(breakdown_agg.items(), key=lambda kv: -kv[1])
    ]

    # Trends — chronological order (oldest first) for charting
    ordered = list(reversed(records))
    oil_trend = [TrendPoint(label=f"#{r.batch_id}", value=r.total_oil_tons) for r in ordered]
    revenue_trend = [TrendPoint(label=f"#{r.batch_id}", value=r.total_revenue_usd) for r in ordered]

    return DashboardOut(
        kpis=kpis,
        plastic_breakdown=plastic_breakdown,
        oil_yield_trend=oil_trend,
        revenue_trend=revenue_trend,
    )
