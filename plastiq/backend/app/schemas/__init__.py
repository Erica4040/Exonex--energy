from app.schemas.auth import UserCreate, UserOut, LoginRequest, Token  # noqa: F401
from app.schemas.facility import (  # noqa: F401
    FacilityCreate, FacilityOut, ScanSourceCreate, ScanSourceOut,
    AISettingsUpdate, AISettingsOut,
)
from app.schemas.waste import (  # noqa: F401
    WasteBatchCreate, WasteBatchOut, DetectionRunCreate, DetectionRunOut,
    DetectedItemOut, BoundingBoxOut, CompositionLineOut,
)
from app.schemas.report import (  # noqa: F401
    PredictionReportOut, GenerateReportRequest, SuitabilityLineOut,
    YieldLineOut, RevenueLineOut, RiskFlagOut, RecommendationOut, AssumptionOut,
)
from app.schemas.dashboard import (  # noqa: F401
    KPISnapshot, PlasticTypeBreakdown, TrendPoint, DashboardOut,
)
