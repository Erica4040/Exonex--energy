"""
Demo data seeding — runs once on first boot (when SEED_DEMO_DATA=true and the
database is empty) so the system is immediately explorable: an admin account,
a demo facility with scan sources, a few waste batches with realistic
detections, and generated prediction reports.

Default login after seeding:
    email:    admin@plastiq.demo
    password: ChangeMe123!
"""

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.facility import AISettings, Facility, ScanSource, ScanSourceType
from app.models.user import User, UserRole
from app.models.waste import BatchStatus, DetectedItem, DetectionRun, PlasticTypeEnum, WasteBatch
from app.ml.detector import SimulatedDetector


DEMO_ADMIN_EMAIL = "admin@plastiq.demo"
DEMO_ADMIN_PASSWORD = "ChangeMe123!"


def seed_if_empty(db: Session) -> None:
    if db.query(User).first() is not None:
        return  # already seeded (or real data exists) — never overwrite

    _seed(db)


def _seed(db: Session) -> None:
    admin = User(
        email=DEMO_ADMIN_EMAIL,
        full_name="Demo Administrator",
        hashed_password=hash_password(DEMO_ADMIN_PASSWORD),
        role=UserRole.ADMIN,
    )
    plant_manager = User(
        email="manager@plastiq.demo",
        full_name="Plant Manager Demo",
        hashed_password=hash_password(DEMO_ADMIN_PASSWORD),
        role=UserRole.PLANT_MANAGER,
    )
    operator = User(
        email="operator@plastiq.demo",
        full_name="Operator Demo",
        hashed_password=hash_password(DEMO_ADMIN_PASSWORD),
        role=UserRole.OPERATOR,
    )
    executive = User(
        email="exec@plastiq.demo",
        full_name="Executive Demo",
        hashed_password=hash_password(DEMO_ADMIN_PASSWORD),
        role=UserRole.EXECUTIVE,
    )
    db.add_all([admin, plant_manager, operator, executive])
    db.flush()

    facility = Facility(
        name="Kumasi Pyrolysis & Recovery Plant",
        location="Kumasi, Ashanti Region, Ghana",
        facility_type="pyrolysis_plant",
    )
    db.add(facility)
    db.flush()

    db.add(AISettings(facility_id=facility.id))

    sources = [
        ScanSource(facility_id=facility.id, name="Conveyor Cam 1", source_type=ScanSourceType.CONVEYOR,
                   location_note="Intake Conveyor Belt, Bay A"),
        ScanSource(facility_id=facility.id, name="Gate CCTV", source_type=ScanSourceType.CCTV,
                   location_note="Main Gate Weighbridge"),
        ScanSource(facility_id=facility.id, name="Sorting Drone 1", source_type=ScanSourceType.DRONE,
                   location_note="Open-air sorting yard"),
    ]
    db.add_all(sources)
    db.flush()

    detector = SimulatedDetector()

    demo_batches = [
        ("BATCH-0001", "Municipal collection route 7", sources[0]),
        ("BATCH-0002", "Industrial packaging offcuts - Plant B", sources[1]),
        ("BATCH-0003", "Mixed landfill reclaim, Zone C", sources[2]),
        ("BATCH-0004", "Municipal collection route 12", sources[0]),
        ("BATCH-0005", "Recycling center drop-off bulk lot", sources[1]),
    ]

    for code, desc, source in demo_batches:
        batch = WasteBatch(
            facility_id=facility.id,
            batch_code=code,
            source_description=desc,
            status=BatchStatus.RECEIVED,
        )
        db.add(batch)
        db.flush()

        # Deterministic simulated image ref per batch so results are stable across reseeds.
        fake_image_ref = f"/mnt/seed-images/{code}.jpg"
        result = detector.detect(fake_image_ref, source=source.source_type.value.lower())

        run = DetectionRun(
            batch_id=batch.id,
            scan_source_id=source.id,
            image_ref=fake_image_ref,
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
        db.flush()

        total_kg = 0.0
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
            total_kg += d.estimated_weight_kg

        batch.total_weight_tons = round(total_kg / 1000.0, 4)
        batch.status = BatchStatus.SCANNED

    db.commit()
