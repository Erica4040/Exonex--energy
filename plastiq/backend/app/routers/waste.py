"""
Core scanning workflow:
  1. Create a waste batch (Step 1: Receive waste)
  2. Upload an image for that batch (Module 1)
  3. Run detection on the image (Module 2/3) — populates DetectedItems
  4. Read back composition (aggregated detections) for the batch
"""

import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.ml.detector import get_detector
from app.models.facility import ScanSource
from app.models.user import User
from app.models.waste import (
    BatchStatus,
    DetectedItem,
    DetectionRun,
    PlasticTypeEnum,
    WasteBatch,
)
from app.schemas.waste import (
    CompositionLineOut,
    DetectionRunCreate,
    DetectionRunOut,
    WasteBatchCreate,
    WasteBatchOut,
)

router = APIRouter(prefix="/waste", tags=["Waste & Detection"])

KG_PER_TON = 1000.0


@router.post("/batches", response_model=WasteBatchOut, dependencies=[Depends(require_permission("trigger_detection"))])
def create_batch(payload: WasteBatchCreate, db: Session = Depends(get_db)):
    existing = db.query(WasteBatch).filter(WasteBatch.batch_code == payload.batch_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Batch code already exists.")
    batch = WasteBatch(**payload.model_dump())
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


@router.get("/batches", response_model=List[WasteBatchOut])
def list_batches(
    facility_id: int | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = db.query(WasteBatch)
    if facility_id:
        q = q.filter(WasteBatch.facility_id == facility_id)
    return q.order_by(WasteBatch.id.desc()).all()


@router.get("/batches/{batch_id}", response_model=WasteBatchOut)
def get_batch(batch_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    batch = db.query(WasteBatch).filter(WasteBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    return batch


@router.post("/batches/{batch_id}/upload-image", dependencies=[Depends(require_permission("trigger_detection"))])
async def upload_image(batch_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    batch = db.query(WasteBatch).filter(WasteBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in app_settings.ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {app_settings.ALLOWED_IMAGE_EXTENSIONS}",
        )

    os.makedirs(app_settings.UPLOAD_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(app_settings.UPLOAD_DIR, stored_name)

    contents = await file.read()
    max_bytes = app_settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {app_settings.MAX_UPLOAD_SIZE_MB}MB limit.")

    with open(stored_path, "wb") as f:
        f.write(contents)

    return {"image_path": stored_path, "original_filename": file.filename}


@router.post("/detect", response_model=DetectionRunOut, dependencies=[Depends(require_permission("trigger_detection"))])
def run_detection(payload: DetectionRunCreate, db: Session = Depends(get_db)):
    """
    Module 2/3: runs the active detector (simulated or real YOLO, see
    ml/detector.py) against an already-uploaded image, persists the detected
    items, and advances the batch to SCANNED.
    """
    batch = db.query(WasteBatch).filter(WasteBatch.id == payload.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    if payload.scan_source_id is not None:
        source = db.query(ScanSource).filter(ScanSource.id == payload.scan_source_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Scan source not found.")
        source_type = source.source_type.value.lower()
    else:
        source_type = "cctv"

    if not os.path.exists(payload.image_path):
        raise HTTPException(
            status_code=400,
            detail="image_path does not exist on the server. Upload it first via /waste/batches/{id}/upload-image.",
        )

    detector = get_detector()
    result = detector.detect(payload.image_path, source=source_type)

    run = DetectionRun(
        batch_id=batch.id,
        scan_source_id=payload.scan_source_id,
        image_ref=result.image_ref,
        model_name=result.model_name,
        model_version=result.model_version,
        raw_detections_json=[
            {
                "plastic_type": d.plastic_type.value,
                "confidence": d.confidence,
                "bbox": {"x_min": d.bbox.x_min, "y_min": d.bbox.y_min, "x_max": d.bbox.x_max, "y_max": d.bbox.y_max},
                "estimated_weight_kg": d.estimated_weight_kg,
            }
            for d in result.detections
        ],
    )
    db.add(run)
    db.flush()  # get run.id without full commit yet

    for d in result.detections:
        db.add(DetectedItem(
            detection_run_id=run.id,
            plastic_type=PlasticTypeEnum(d.plastic_type.value),
            confidence=d.confidence,
            bbox_x_min=d.bbox.x_min,
            bbox_y_min=d.bbox.y_min,
            bbox_x_max=d.bbox.x_max,
            bbox_y_max=d.bbox.y_max,
            estimated_weight_kg=d.estimated_weight_kg,
        ))

    # Roll up total detected weight into the batch if no weighbridge figure was given.
    total_detected_kg = sum(d.estimated_weight_kg for d in result.detections)
    if batch.total_weight_tons is None:
        batch.total_weight_tons = round(total_detected_kg / KG_PER_TON, 4)
    batch.status = BatchStatus.SCANNED

    db.commit()
    db.refresh(run)
    return run


@router.get("/batches/{batch_id}/detection-runs", response_model=List[DetectionRunOut])
def list_detection_runs(batch_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.query(DetectionRun).filter(DetectionRun.batch_id == batch_id).order_by(DetectionRun.id).all()


@router.get("/batches/{batch_id}/composition", response_model=List[CompositionLineOut])
def get_batch_composition(batch_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Aggregates all detected items across all detection runs for a batch into per-polymer totals."""
    batch = db.query(WasteBatch).filter(WasteBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    runs = db.query(DetectionRun).filter(DetectionRun.batch_id == batch_id).all()
    agg: dict[str, dict] = {}
    for run in runs:
        for item in run.items:
            key = item.plastic_type.value
            bucket = agg.setdefault(key, {"weight_kg": 0.0, "count": 0, "conf_sum": 0.0})
            bucket["weight_kg"] += item.estimated_weight_kg
            bucket["count"] += 1
            bucket["conf_sum"] += item.confidence

    lines = []
    for ptype, bucket in agg.items():
        lines.append(CompositionLineOut(
            plastic_type=PlasticTypeEnum(ptype),
            weight_tons=round(bucket["weight_kg"] / KG_PER_TON, 4),
            item_count=bucket["count"],
            avg_confidence=round(bucket["conf_sum"] / bucket["count"], 4) if bucket["count"] else 0.0,
        ))
    return lines
