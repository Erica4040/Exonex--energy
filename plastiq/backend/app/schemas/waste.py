from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.waste import BatchStatus, PlasticTypeEnum


class WasteBatchCreate(BaseModel):
    facility_id: int
    batch_code: str = Field(min_length=1, max_length=50)
    source_description: Optional[str] = None
    total_weight_tons: Optional[float] = Field(
        default=None, ge=0,
        description="Optional weighbridge reading; if omitted, derived from detected item weights",
    )


class WasteBatchOut(BaseModel):
    id: int
    facility_id: int
    batch_code: str
    source_description: Optional[str]
    total_weight_tons: Optional[float]
    status: BatchStatus
    received_at: datetime

    class Config:
        from_attributes = True


class BoundingBoxOut(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class DetectedItemOut(BaseModel):
    plastic_type: PlasticTypeEnum
    confidence: float
    bbox: BoundingBoxOut
    estimated_weight_kg: float


class DetectionRunCreate(BaseModel):
    batch_id: int
    scan_source_id: Optional[int] = None
    image_path: str = Field(description="Server-side path of the previously uploaded image")


class DetectionRunOut(BaseModel):
    id: int
    batch_id: int
    scan_source_id: Optional[int]
    image_ref: Optional[str]
    model_name: str
    model_version: str
    items: List[DetectedItemOut]
    created_at: datetime

    class Config:
        from_attributes = True


class CompositionLineOut(BaseModel):
    plastic_type: PlasticTypeEnum
    weight_tons: float
    item_count: int
    avg_confidence: float
