from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models.facility import AISettings
from app.models.report import PredictionReportRecord, RecommendationRecord, RiskFlagRecord
from app.models.user import User
from app.models.waste import DetectionRun, WasteBatch, BatchStatus
from app.schemas.report import GenerateReportRequest, PredictionReportOut
from app.services.prediction_engine import build_prediction_report, CompositionItem
from app.ml.polymer_reference import PlasticType

router = APIRouter(prefix="/reports", tags=["Prediction Reports"])

KG_PER_TON = 1000.0


def _get_composition(db: Session, batch_id: int) -> list[CompositionItem]:
    runs = db.query(DetectionRun).filter(DetectionRun.batch_id == batch_id).all()
    agg: dict[str, dict] = {}
    for run in runs:
        for item in run.items:
            key = item.plastic_type.value
            bucket = agg.setdefault(key, {"weight_kg": 0.0, "count": 0, "conf_sum": 0.0})
            bucket["weight_kg"] += item.estimated_weight_kg
            bucket["count"] += 1
            bucket["conf_sum"] += item.confidence

    composition = []
    for ptype, bucket in agg.items():
        composition.append(CompositionItem(
            plastic_type=PlasticType(ptype),
            weight_tons=round(bucket["weight_kg"] / KG_PER_TON, 4),
            avg_confidence=round(bucket["conf_sum"] / bucket["count"], 4) if bucket["count"] else 0.0,
            item_count=bucket["count"],
        ))
    return composition


@router.post("/generate", response_model=PredictionReportOut, dependencies=[Depends(require_permission("view_forecasts"))])
def generate_report(payload: GenerateReportRequest, db: Session = Depends(get_db)):
    batch = db.query(WasteBatch).filter(WasteBatch.id == payload.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    composition = _get_composition(db, batch.id)
    if not composition:
        raise HTTPException(
            status_code=400,
            detail="No detections found for this batch yet. Run detection before generating a report.",
        )

    ai_settings = db.query(AISettings).filter(AISettings.facility_id == batch.facility_id).first()

    pricing = None
    processing_cost = None
    target_margin = None
    if ai_settings:
        pricing = {
            "pyrolysis_oil_usd_per_ton": ai_settings.pyrolysis_oil_usd_per_ton,
            "carbon_black_usd_per_ton": ai_settings.carbon_black_usd_per_ton,
            "wax_usd_per_ton": ai_settings.wax_usd_per_ton,
            "pyrolysis_gas_usd_per_ton": ai_settings.pyrolysis_gas_usd_per_ton,
        }
        processing_cost = ai_settings.processing_cost_usd_per_ton
        target_margin = ai_settings.target_profit_margin_pct

    yield_overrides = None
    if ai_settings and ai_settings.yield_overrides_json:
        yield_overrides = {
            PlasticType(k): v for k, v in ai_settings.yield_overrides_json.items()
        }

    report = build_prediction_report(
        composition=composition,
        pricing=pricing,
        yield_overrides=yield_overrides,
        machine_utilization_pct=payload.machine_utilization_pct,
        target_profit_margin_pct=target_margin,
        processing_cost_usd_per_ton=processing_cost,
    )

    # Persist
    record = PredictionReportRecord(
        batch_id=batch.id,
        total_waste_tons=report.total_waste_tons,
        suitable_feedstock_tons=report.suitable_feedstock_tons,
        rejected_tons=report.rejected_tons,
        contamination_pct=report.contamination_pct,
        total_oil_tons=report.yield_summary.total_oil_tons,
        total_gas_tons=report.yield_summary.total_gas_tons,
        total_char_tons=report.yield_summary.total_char_tons,
        total_wax_tons=report.yield_summary.total_wax_tons,
        total_revenue_usd=report.revenue_summary.total_revenue_usd,
        composition_json=[
            {"plastic_type": c.plastic_type.value, "weight_tons": c.weight_tons,
             "avg_confidence": c.avg_confidence, "item_count": c.item_count}
            for c in report.composition
        ],
        suitability_json=[
            {"plastic_type": s.plastic_type.value, "weight_tons": s.weight_tons,
             "suitability": s.suitability.value, "reason": s.reason,
             "included_in_feedstock": s.included_in_feedstock,
             "contamination_pct_of_total": s.contamination_pct_of_total}
            for s in report.suitability_lines
        ],
        yield_lines_json=[
            {"plastic_type": y.plastic_type.value, "input_tons": y.input_tons,
             "oil_tons": y.oil_tons, "gas_tons": y.gas_tons,
             "char_tons": y.char_tons, "wax_tons": y.wax_tons}
            for y in report.yield_summary.lines
        ],
        revenue_lines_json=[
            {"product": r.product, "quantity_tons": r.quantity_tons,
             "price_usd_per_ton": r.price_usd_per_ton, "revenue_usd": r.revenue_usd}
            for r in report.revenue_summary.lines
        ],
        assumptions_json=[
            {"field": a.field, "assumption": a.assumption, "confidence_pct": a.confidence_pct}
            for a in report.assumptions
        ],
        executive_summary=report.executive_summary,
    )
    db.add(record)
    db.flush()

    for risk in report.risks:
        db.add(RiskFlagRecord(report_id=record.id, severity=risk.severity, code=risk.code, message=risk.message))
    for rec in report.recommendations:
        db.add(RecommendationRecord(report_id=record.id, priority=rec.priority, action=rec.action))

    batch.status = BatchStatus.PROCESSED
    db.commit()
    db.refresh(record)

    return _record_to_schema(record)


def _record_to_schema(record: PredictionReportRecord) -> PredictionReportOut:
    yield_lines = record.yield_lines_json or []
    overall_oil_yield_pct = (
        round((record.total_oil_tons / record.total_waste_tons) * 100, 2)
        if record.total_waste_tons else 0.0
    )
    return PredictionReportOut(
        id=record.id,
        batch_id=record.batch_id,
        total_waste_tons=record.total_waste_tons,
        suitable_feedstock_tons=record.suitable_feedstock_tons,
        rejected_tons=record.rejected_tons,
        contamination_pct=record.contamination_pct,
        suitability_lines=record.suitability_json or [],
        yield_lines=yield_lines,
        total_oil_tons=record.total_oil_tons,
        total_gas_tons=record.total_gas_tons,
        total_char_tons=record.total_char_tons,
        total_wax_tons=record.total_wax_tons,
        overall_oil_yield_pct=overall_oil_yield_pct,
        revenue_lines=record.revenue_lines_json or [],
        total_revenue_usd=record.total_revenue_usd,
        risks=[{"severity": r.severity, "code": r.code, "message": r.message} for r in record.risks],
        recommendations=[{"priority": r.priority, "action": r.action} for r in record.recommendations],
        assumptions=record.assumptions_json or [],
        executive_summary=record.executive_summary or "",
        created_at=record.created_at,
    )


@router.get("/{report_id}", response_model=PredictionReportOut)
def get_report(report_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    record = db.query(PredictionReportRecord).filter(PredictionReportRecord.id == report_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Report not found.")
    return _record_to_schema(record)


@router.get("/batch/{batch_id}", response_model=List[PredictionReportOut])
def get_reports_for_batch(batch_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    records = db.query(PredictionReportRecord).filter(PredictionReportRecord.batch_id == batch_id).order_by(
        PredictionReportRecord.id.desc()
    ).all()
    return [_record_to_schema(r) for r in records]
