from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models.facility import AISettings, Facility, ScanSource
from app.models.user import User
from app.schemas.facility import (
    AISettingsOut,
    AISettingsUpdate,
    FacilityCreate,
    FacilityOut,
    ScanSourceCreate,
    ScanSourceOut,
)

router = APIRouter(prefix="/facilities", tags=["Facilities"])


@router.post("", response_model=FacilityOut, dependencies=[Depends(require_permission("configure_facilities"))])
def create_facility(payload: FacilityCreate, db: Session = Depends(get_db)):
    facility = Facility(**payload.model_dump())
    db.add(facility)
    db.commit()
    db.refresh(facility)

    # Every facility gets default AI settings immediately so prediction
    # requests never fail due to missing config.
    db.add(AISettings(facility_id=facility.id))
    db.commit()

    return facility


@router.get("", response_model=list[FacilityOut])
def list_facilities(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.query(Facility).order_by(Facility.id).all()


@router.get("/{facility_id}", response_model=FacilityOut)
def get_facility(facility_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found.")
    return facility


@router.post(
    "/scan-sources", response_model=ScanSourceOut,
    dependencies=[Depends(require_permission("configure_facilities"))],
)
def create_scan_source(payload: ScanSourceCreate, db: Session = Depends(get_db)):
    facility = db.query(Facility).filter(Facility.id == payload.facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found.")
    source = ScanSource(**payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("/{facility_id}/scan-sources", response_model=list[ScanSourceOut])
def list_scan_sources(facility_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.query(ScanSource).filter(ScanSource.facility_id == facility_id).all()


@router.get("/{facility_id}/ai-settings", response_model=AISettingsOut)
def get_ai_settings(facility_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    settings_row = db.query(AISettings).filter(AISettings.facility_id == facility_id).first()
    if not settings_row:
        raise HTTPException(status_code=404, detail="AI settings not found for this facility.")
    return settings_row


@router.patch(
    "/{facility_id}/ai-settings", response_model=AISettingsOut,
    dependencies=[Depends(require_permission("configure_ai_settings"))],
)
def update_ai_settings(facility_id: int, payload: AISettingsUpdate, db: Session = Depends(get_db)):
    settings_row = db.query(AISettings).filter(AISettings.facility_id == facility_id).first()
    if not settings_row:
        raise HTTPException(status_code=404, detail="AI settings not found for this facility.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings_row, field, value)

    db.commit()
    db.refresh(settings_row)
    return settings_row
