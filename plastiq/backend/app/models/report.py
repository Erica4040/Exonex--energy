"""
Persisted prediction reports — the saved output of the prediction engine for
a given batch, plus its risk flags and recommendations, so history/BI
reporting (Module 6/7) can query past runs rather than recomputing.
"""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class PredictionReportRecord(Base):
    __tablename__ = "prediction_reports"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("waste_batches.id"), nullable=False)

    total_waste_tons = Column(Float, nullable=False)
    suitable_feedstock_tons = Column(Float, nullable=False)
    rejected_tons = Column(Float, nullable=False)
    contamination_pct = Column(Float, nullable=False)

    total_oil_tons = Column(Float, nullable=False)
    total_gas_tons = Column(Float, nullable=False)
    total_char_tons = Column(Float, nullable=False)
    total_wax_tons = Column(Float, nullable=False)

    total_revenue_usd = Column(Float, nullable=False)

    composition_json = Column(JSON, nullable=True)
    suitability_json = Column(JSON, nullable=True)
    yield_lines_json = Column(JSON, nullable=True)
    revenue_lines_json = Column(JSON, nullable=True)
    assumptions_json = Column(JSON, nullable=True)

    executive_summary = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    batch = relationship("WasteBatch", back_populates="prediction_reports")
    risks = relationship("RiskFlagRecord", back_populates="report", cascade="all, delete-orphan")
    recommendations = relationship("RecommendationRecord", back_populates="report", cascade="all, delete-orphan")


class RiskFlagRecord(Base):
    __tablename__ = "risk_flags"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("prediction_reports.id"), nullable=False)
    severity = Column(String(20), nullable=False)  # INFO | WARNING | CRITICAL
    code = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("PredictionReportRecord", back_populates="risks")


class RecommendationRecord(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("prediction_reports.id"), nullable=False)
    priority = Column(String(20), nullable=False)  # LOW | MEDIUM | HIGH
    action = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    report = relationship("PredictionReportRecord", back_populates="recommendations")
