from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.waste import PlasticTypeEnum


class SuitabilityLineOut(BaseModel):
    plastic_type: PlasticTypeEnum
    weight_tons: float
    suitability: str
    reason: str
    included_in_feedstock: bool
    contamination_pct_of_total: float


class YieldLineOut(BaseModel):
    plastic_type: PlasticTypeEnum
    input_tons: float
    oil_tons: float
    gas_tons: float
    char_tons: float
    wax_tons: float


class RevenueLineOut(BaseModel):
    product: str
    quantity_tons: float
    price_usd_per_ton: float
    revenue_usd: float


class RiskFlagOut(BaseModel):
    severity: str
    code: str
    message: str


class RecommendationOut(BaseModel):
    priority: str
    action: str


class AssumptionOut(BaseModel):
    field: str
    assumption: str
    confidence_pct: float


class PredictionReportOut(BaseModel):
    """
    Full structured AI response — mirrors the spec's AI RESPONSE FORMAT:
    Production Summary, Required Raw Materials (here: composition), Material
    Availability (feedstock), Cost/Revenue/Profit Forecast, Production Risks,
    Waste Prediction, Recommended Actions, Executive Summary.
    """
    id: Optional[int] = None
    batch_id: int

    total_waste_tons: float
    suitable_feedstock_tons: float
    rejected_tons: float
    contamination_pct: float

    suitability_lines: List[SuitabilityLineOut]
    yield_lines: List[YieldLineOut]
    total_oil_tons: float
    total_gas_tons: float
    total_char_tons: float
    total_wax_tons: float
    overall_oil_yield_pct: float

    revenue_lines: List[RevenueLineOut]
    total_revenue_usd: float

    risks: List[RiskFlagOut]
    recommendations: List[RecommendationOut]
    assumptions: List[AssumptionOut]

    executive_summary: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GenerateReportRequest(BaseModel):
    batch_id: int
    machine_utilization_pct: Optional[float] = None
