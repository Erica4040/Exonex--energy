from typing import Optional

from pydantic import BaseModel, Field

from app.models.facility import ScanSourceType


class FacilityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    location: Optional[str] = None
    facility_type: Optional[str] = Field(
        default="pyrolysis_plant",
        description="landfill | recycling_center | municipal | pyrolysis_plant",
    )


class FacilityOut(BaseModel):
    id: int
    name: str
    location: Optional[str]
    facility_type: Optional[str]

    class Config:
        from_attributes = True


class ScanSourceCreate(BaseModel):
    facility_id: int
    name: str = Field(min_length=1, max_length=255)
    source_type: ScanSourceType
    location_note: Optional[str] = None


class ScanSourceOut(BaseModel):
    id: int
    facility_id: int
    name: str
    source_type: ScanSourceType
    location_note: Optional[str]
    is_active: int

    class Config:
        from_attributes = True


class AISettingsUpdate(BaseModel):
    pyrolysis_oil_usd_per_ton: Optional[float] = None
    carbon_black_usd_per_ton: Optional[float] = None
    wax_usd_per_ton: Optional[float] = None
    pyrolysis_gas_usd_per_ton: Optional[float] = None
    processing_cost_usd_per_ton: Optional[float] = None
    target_profit_margin_pct: Optional[float] = None
    pvc_contamination_warning_pct: Optional[float] = None
    pvc_contamination_critical_pct: Optional[float] = None
    machine_utilization_warning_pct: Optional[float] = None
    safety_stock_feedstock_tons: Optional[float] = None
    low_confidence_threshold: Optional[float] = None
    detector_backend: Optional[str] = None


class AISettingsOut(BaseModel):
    facility_id: int
    pyrolysis_oil_usd_per_ton: float
    carbon_black_usd_per_ton: float
    wax_usd_per_ton: float
    pyrolysis_gas_usd_per_ton: float
    processing_cost_usd_per_ton: float
    target_profit_margin_pct: float
    pvc_contamination_warning_pct: float
    pvc_contamination_critical_pct: float
    machine_utilization_warning_pct: float
    safety_stock_feedstock_tons: float
    low_confidence_threshold: float
    detector_backend: str

    class Config:
        from_attributes = True
