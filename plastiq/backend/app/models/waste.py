"""
Core operational entities: a waste batch arriving for scanning, the detection
run performed on it, and the individual detected items (Module 2/3 output).
"""

import enum

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BatchStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"          # waste has arrived, awaiting scan
    SCANNED = "SCANNED"             # detection complete, composition known
    PROCESSED = "PROCESSED"         # sent to pyrolysis, run logged
    REJECTED = "REJECTED"           # entire batch rejected (e.g. all hazardous)


class WasteBatch(Base):
    """One intake of waste material — from a truck, landfill load, or conveyor session."""
    __tablename__ = "waste_batches"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    batch_code = Column(String(50), unique=True, index=True, nullable=False)
    source_description = Column(String(255), nullable=True)  # e.g. "Municipal collection route 7"
    total_weight_tons = Column(Float, nullable=True)  # filled once scan/weighbridge data available
    status = Column(Enum(BatchStatus), default=BatchStatus.RECEIVED)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    facility = relationship("Facility", back_populates="waste_batches")
    detection_runs = relationship("DetectionRun", back_populates="batch", cascade="all, delete-orphan")
    prediction_reports = relationship("PredictionReportRecord", back_populates="batch", cascade="all, delete-orphan")


class DetectionRun(Base):
    """One AI detection pass over one or more images/frames for a batch."""
    __tablename__ = "detection_runs"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("waste_batches.id"), nullable=False)
    scan_source_id = Column(Integer, ForeignKey("scan_sources.id"), nullable=True)
    image_ref = Column(String(500), nullable=True)  # stored path/URL of source image
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(100), nullable=False)
    raw_detections_json = Column(JSON, nullable=True)  # full Detection list, serialized
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    batch = relationship("WasteBatch", back_populates="detection_runs")
    items = relationship("DetectedItem", back_populates="detection_run", cascade="all, delete-orphan")


class PlasticTypeEnum(str, enum.Enum):
    PET = "PET"
    HDPE = "HDPE"
    LDPE = "LDPE"
    PP = "PP"
    PS = "PS"
    PVC = "PVC"
    MIXED = "MIXED"
    OTHER = "OTHER"


class DetectedItem(Base):
    """A single bounding-box detection (one physical item) within a detection run."""
    __tablename__ = "detected_items"

    id = Column(Integer, primary_key=True, index=True)
    detection_run_id = Column(Integer, ForeignKey("detection_runs.id"), nullable=False)
    plastic_type = Column(Enum(PlasticTypeEnum), nullable=False)
    confidence = Column(Float, nullable=False)
    bbox_x_min = Column(Float, nullable=False)
    bbox_y_min = Column(Float, nullable=False)
    bbox_x_max = Column(Float, nullable=False)
    bbox_y_max = Column(Float, nullable=False)
    estimated_weight_kg = Column(Float, default=0.0)

    detection_run = relationship("DetectionRun", back_populates="items")
