from typing import List

from pydantic import BaseModel


class KPISnapshot(BaseModel):
    """
    KPI Dashboard fields, adapted from the reference KPI DASHBOARD section:
    Production Efficiency, Material Utilization, Machine Utilization,
    Inventory Accuracy, Production Yield, Waste %, Downtime %, Profit Margin,
    Revenue, Net Profit — remapped to pyrolysis-plant equivalents.
    """
    period_label: str  # e.g. "Last 30 days"

    total_waste_scanned_tons: float
    total_suitable_feedstock_tons: float
    feedstock_utilization_pct: float  # suitable / total scanned

    total_oil_produced_tons: float
    overall_oil_yield_pct: float

    total_revenue_usd: float
    estimated_total_cost_usd: float
    estimated_net_profit_usd: float
    estimated_profit_margin_pct: float

    avg_pvc_contamination_pct: float
    open_critical_risks: int
    open_warning_risks: int

    batches_processed: int


class PlasticTypeBreakdown(BaseModel):
    plastic_type: str
    total_weight_tons: float
    pct_of_total: float


class TrendPoint(BaseModel):
    label: str  # date or batch code
    value: float


class DashboardOut(BaseModel):
    kpis: KPISnapshot
    plastic_breakdown: List[PlasticTypeBreakdown]
    oil_yield_trend: List[TrendPoint]
    revenue_trend: List[TrendPoint]
