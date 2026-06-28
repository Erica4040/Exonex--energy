"""Facilities, scan sources (cameras/drones), and per-facility AI settings."""

import enum

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Facility(Base):
    """A landfill, recycling center, municipal waste facility, or plastic-to-fuel plant."""
    __tablename__ = "facilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    facility_type = Column(String(100), nullable=True)  # "landfill" | "recycling_center" | "municipal" | "pyrolysis_plant"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scan_sources = relationship("ScanSource", back_populates="facility", cascade="all, delete-orphan")
    waste_batches = relationship("WasteBatch", back_populates="facility", cascade="all, delete-orphan")
    ai_settings = relationship("AISettings", back_populates="facility", uselist=False, cascade="all, delete-orphan")


class ScanSourceType(str, enum.Enum):
    CCTV = "CCTV"
    MOBILE = "MOBILE"
    DRONE = "DRONE"
    CONVEYOR = "CONVEYOR"


class ScanSource(Base):
    """Module 1: Waste Image Acquisition — a registered camera/drone/conveyor feed."""
    __tablename__ = "scan_sources"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    name = Column(String(255), nullable=False)
    source_type = Column(Enum(ScanSourceType), nullable=False)
    location_note = Column(String(255), nullable=True)  # e.g. "Conveyor Belt 2, Bay A"
    is_active = Column(Integer, default=1)  # boolean-as-int for SQLite friendliness
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    facility = relationship("Facility", back_populates="scan_sources")


class AISettings(Base):
    """
    Configurable AI/business parameters per facility — pricing, risk thresholds,
    detector backend overrides, and target margins. Mirrors the generic
    "Configure AI settings" admin capability from the reference role matrix.
    """
    __tablename__ = "ai_settings"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), unique=True, nullable=False)

    pyrolysis_oil_usd_per_ton = Column(Float, default=600.0)
    carbon_black_usd_per_ton = Column(Float, default=250.0)
    wax_usd_per_ton = Column(Float, default=300.0)
    pyrolysis_gas_usd_per_ton = Column(Float, default=0.0)

    processing_cost_usd_per_ton = Column(Float, default=150.0)
    target_profit_margin_pct = Column(Float, default=15.0)

    pvc_contamination_warning_pct = Column(Float, default=2.0)
    pvc_contamination_critical_pct = Column(Float, default=5.0)
    machine_utilization_warning_pct = Column(Float, default=90.0)
    safety_stock_feedstock_tons = Column(Float, default=1.0)
    low_confidence_threshold = Column(Float, default=0.60)

    detector_backend = Column(String(50), default="simulated")  # "simulated" | "yolo"
    yield_overrides_json = Column(JSON, nullable=True)  # plant-calibrated yield coefficients

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    facility = relationship("Facility", back_populates="ai_settings")
