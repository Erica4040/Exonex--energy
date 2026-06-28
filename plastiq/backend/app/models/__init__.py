"""
Import all ORM models here so that a single `from app.models import *` (or even
just importing this package) registers every table on Base.metadata before
Base.metadata.create_all(engine) is called in main.py.
"""

from app.models.user import User, UserRole, ROLE_PERMISSIONS  # noqa: F401
from app.models.facility import Facility, ScanSource, ScanSourceType, AISettings  # noqa: F401
from app.models.waste import (  # noqa: F401
    WasteBatch,
    BatchStatus,
    DetectionRun,
    DetectedItem,
    PlasticTypeEnum,
)
from app.models.report import (  # noqa: F401
    PredictionReportRecord,
    RiskFlagRecord,
    RecommendationRecord,
)
