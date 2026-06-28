"""
User accounts and role-based access control.

Roles are adapted from the secondary reference document's USER ROLES section,
remapped from generic manufacturing to the plastic-pyrolysis domain:

  Administrator      -> ADMIN              (manage users, facilities, lines, AI settings)
  Production Manager -> PLANT_MANAGER       (plan production runs, approve schedules)
  Inventory Manager   -> FEEDSTOCK_MANAGER  (manage waste intake stock, suitable feedstock)
  Machine Operator    -> OPERATOR           (operate scanners/reactors, log runs)
  Executive           -> EXECUTIVE          (dashboards, KPIs, BI reports)
"""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    PLANT_MANAGER = "PLANT_MANAGER"
    FEEDSTOCK_MANAGER = "FEEDSTOCK_MANAGER"
    OPERATOR = "OPERATOR"
    EXECUTIVE = "EXECUTIVE"


# Declarative permission matrix — used by core/permissions.py to authorize requests.
ROLE_PERMISSIONS = {
    UserRole.ADMIN: {
        "manage_users", "configure_facilities", "configure_lines",
        "configure_pricing", "configure_ai_settings", "view_all_reports",
        "view_dashboards", "view_kpis", "view_bi_reports",
        "create_runs", "view_forecasts", "monitor_operations", "approve_schedules",
        "manage_stock", "receive_materials", "issue_materials", "monitor_inventory",
        "update_machine_status", "record_production", "submit_reports",
        "trigger_detection", "view_detections",
    },
    UserRole.PLANT_MANAGER: {
        "create_runs", "view_forecasts", "monitor_operations", "approve_schedules",
        "view_dashboards", "view_kpis", "trigger_detection", "view_detections",
        "monitor_inventory",
    },
    UserRole.FEEDSTOCK_MANAGER: {
        "manage_stock", "receive_materials", "issue_materials", "monitor_inventory",
        "view_detections", "view_dashboards",
    },
    UserRole.OPERATOR: {
        "update_machine_status", "record_production", "submit_reports",
        "trigger_detection", "view_detections",
    },
    UserRole.EXECUTIVE: {
        "view_dashboards", "view_kpis", "view_bi_reports", "view_all_reports",
        "view_forecasts",
    },
}


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.OPERATOR)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
