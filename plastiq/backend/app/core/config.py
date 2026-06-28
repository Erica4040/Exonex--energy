"""Application configuration. Reads from environment variables with sane defaults."""

import os
from typing import Dict

from app.ml.polymer_reference import PlasticType


def _get_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    PROJECT_NAME: str = "PlastiQ — Plastic Waste Detection & Pyrolysis Yield Intelligence"
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./plastiq.db")

    # --- Auth ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_USE_A_RANDOM_64_CHAR_STRING")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

    # --- CORS ---
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

    # --- Detector backend ---
    # "simulated" (default, works out of the box) or "yolo" (requires ultralytics + trained weights)
    DETECTOR_BACKEND: str = os.getenv("DETECTOR_BACKEND", "simulated")
    YOLO_MODEL_PATH: str = os.getenv("YOLO_MODEL_PATH", "./models/plastic_yolo.pt")
    # Map of YOLO class index -> PlasticType. MUST match your training run's class order.
    YOLO_CLASS_MAP: Dict[int, PlasticType] = {
        0: PlasticType.PET,
        1: PlasticType.HDPE,
        2: PlasticType.LDPE,
        3: PlasticType.PP,
        4: PlasticType.PS,
        5: PlasticType.PVC,
        6: PlasticType.MIXED,
    }
    YOLO_CONFIDENCE_THRESHOLD: float = float(os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.5"))

    # --- File storage ---
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
    ALLOWED_IMAGE_EXTENSIONS: tuple = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

    # --- Seed/demo data on first boot ---
    SEED_DEMO_DATA: bool = _get_bool("SEED_DEMO_DATA", True)


settings = Settings()
