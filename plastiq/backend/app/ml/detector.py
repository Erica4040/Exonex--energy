"""
Pluggable plastic-detection interface.

Module 2 (AI Plastic Detection) from the spec calls for YOLOv11/YOLOv12 object
detection. This module defines the contract any real detector must satisfy
(`PlasticDetector.detect`), so a trained YOLO model can be dropped in later
without touching any other layer of the system (routers, services, DB).

Two implementations ship with this codebase:
  - SimulatedDetector: deterministic, weight-aware mock detector used until a
    real trained model is available. Lets the whole pipeline (suitability ->
    yield -> revenue -> recommendations -> reporting) run and be demoed today.
  - YoloDetector: real inference adapter for an Ultralytics YOLO .pt model.
    Disabled (raises informative error) until `ultralytics` is installed and
    a model path is configured — see AI Settings -> Computer Vision Model.

Swap which one is active in app/core/config.py (DETECTOR_BACKEND env var).
"""

from __future__ import annotations

import hashlib
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from app.ml.polymer_reference import PlasticType


@dataclass
class BoundingBox:
    x_min: float  # normalized 0-1, relative to image width
    y_min: float
    x_max: float
    y_max: float


@dataclass
class Detection:
    plastic_type: PlasticType
    confidence: float          # 0.0 - 1.0, model confidence for classification
    bbox: BoundingBox
    estimated_weight_kg: float  # derived from bbox area + density heuristic / sensor fusion
    estimated_volume_l: Optional[float] = None
    item_id: str = field(default="")


@dataclass
class DetectionResult:
    source: str                 # "cctv" | "mobile" | "drone" | "conveyor"
    image_ref: str               # path or id of the source frame
    detections: List[Detection]
    model_name: str
    model_version: str
    processed_at_iso: str = ""


class PlasticDetector(ABC):
    """Contract every detection backend must implement."""

    name: str = "base"
    version: str = "0.0"

    @abstractmethod
    def detect(self, image_path: str, source: str = "cctv") -> DetectionResult:
        """Run detection on a single image/frame and return structured detections."""
        raise NotImplementedError

    def detect_batch(self, image_paths: List[str], source: str = "cctv") -> List[DetectionResult]:
        return [self.detect(p, source=source) for p in image_paths]


class SimulatedDetector(PlasticDetector):
    """
    Deterministic mock detector.

    Uses a hash of the image path/bytes as a seed so the same image always
    yields the same simulated detections (useful for demos and tests), while
    different images yield varied, plausible plastic-waste compositions.

    This is clearly a stand-in for a trained CV model — it does NOT look at
    actual pixel content for classification, only for a stable seed and a
    coarse brightness/size heuristic used to vary output. Replace with
    YoloDetector for real production use.
    """

    name = "SimulatedDetector"
    version = "1.0.0-mock"

    # Realistic real-world mix bias: PET and LDPE dominate typical municipal streams.
    TYPE_WEIGHTS = {
        PlasticType.PET: 0.28,
        PlasticType.HDPE: 0.18,
        PlasticType.LDPE: 0.20,
        PlasticType.PP: 0.16,
        PlasticType.PS: 0.08,
        PlasticType.PVC: 0.04,
        PlasticType.MIXED: 0.06,
    }

    def _seed_from_path(self, image_path: str) -> int:
        h = hashlib.sha256(image_path.encode("utf-8")).hexdigest()
        return int(h[:8], 16)

    def detect(self, image_path: str, source: str = "cctv") -> DetectionResult:
        rng = random.Random(self._seed_from_path(image_path))

        num_items = rng.randint(8, 22)
        types = list(self.TYPE_WEIGHTS.keys())
        weights = list(self.TYPE_WEIGHTS.values())

        detections: List[Detection] = []
        for i in range(num_items):
            ptype = rng.choices(types, weights=weights, k=1)[0]
            confidence = round(rng.uniform(0.62, 0.98), 4)

            x_min = rng.uniform(0.0, 0.85)
            y_min = rng.uniform(0.0, 0.85)
            box_w = rng.uniform(0.05, 0.15)
            box_h = rng.uniform(0.05, 0.15)
            bbox = BoundingBox(
                x_min=round(x_min, 4),
                y_min=round(y_min, 4),
                x_max=round(min(1.0, x_min + box_w), 4),
                y_max=round(min(1.0, y_min + box_h), 4),
            )

            # Rough weight heuristic: bbox area as a proxy for item size,
            # scaled by a per-polymer density/typical-item-mass factor.
            area = box_w * box_h
            density_factor_kg = {
                PlasticType.PET: 28.0,
                PlasticType.HDPE: 35.0,
                PlasticType.LDPE: 12.0,
                PlasticType.PP: 22.0,
                PlasticType.PS: 9.0,
                PlasticType.PVC: 40.0,
                PlasticType.MIXED: 25.0,
            }[ptype]
            est_weight = round(area * density_factor_kg * rng.uniform(0.8, 1.2), 3)

            detections.append(
                Detection(
                    plastic_type=ptype,
                    confidence=confidence,
                    bbox=bbox,
                    estimated_weight_kg=max(est_weight, 0.05),
                    item_id=f"det-{i:03d}",
                )
            )

        return DetectionResult(
            source=source,
            image_ref=image_path,
            detections=detections,
            model_name=self.name,
            model_version=self.version,
        )


class YoloDetector(PlasticDetector):
    """
    Real inference adapter for an Ultralytics YOLOv11/YOLOv12 model trained on
    a plastic-polymer dataset (class labels matching PlasticType values).

    To activate:
      1. pip install ultralytics
      2. Place trained weights at the configured MODEL_PATH (see core/config.py)
      3. Set DETECTOR_BACKEND=yolo in environment
      4. Provide a class-index -> PlasticType mapping matching your training run

    Until configured, this raises a clear error rather than silently
    returning fake "real" results.
    """

    name = "YoloDetector"
    version = "uninitialized"

    def __init__(self, model_path: str, class_map: dict, conf_threshold: float = 0.5):
        self.model_path = model_path
        self.class_map = class_map
        self.conf_threshold = conf_threshold
        self._model = None

    def _load(self):
        try:
            from ultralytics import YOLO  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "ultralytics is not installed. Run `pip install ultralytics` "
                "and place a trained model at the configured MODEL_PATH to "
                "use real YOLO detection. Falling back to SimulatedDetector "
                "is recommended until then (DETECTOR_BACKEND=simulated)."
            ) from e
        self._model = YOLO(self.model_path)
        self.version = getattr(self._model, "ckpt_path", self.model_path)

    def detect(self, image_path: str, source: str = "cctv") -> DetectionResult:
        if self._model is None:
            self._load()

        results = self._model.predict(image_path, conf=self.conf_threshold, verbose=False)
        detections: List[Detection] = []

        for i, r in enumerate(results):
            for j, box in enumerate(r.boxes):
                cls_idx = int(box.cls[0])
                conf = float(box.conf[0])
                ptype = self.class_map.get(cls_idx, PlasticType.OTHER)
                xyxyn = box.xyxyn[0].tolist()  # normalized coords

                detections.append(
                    Detection(
                        plastic_type=ptype,
                        confidence=round(conf, 4),
                        bbox=BoundingBox(
                            x_min=xyxyn[0], y_min=xyxyn[1],
                            x_max=xyxyn[2], y_max=xyxyn[3],
                        ),
                        # Real weight requires sensor fusion (scale/volumetric
                        # camera) or a calibrated area->mass regression; until
                        # that calibration exists, this is flagged as a TODO.
                        estimated_weight_kg=0.0,
                        item_id=f"det-{i:03d}-{j:03d}",
                    )
                )

        return DetectionResult(
            source=source,
            image_ref=image_path,
            detections=detections,
            model_name=self.name,
            model_version=str(self.version),
        )


def get_detector() -> PlasticDetector:
    """Factory — reads configuration and returns the active detector backend."""
    from app.core.config import settings

    if settings.DETECTOR_BACKEND == "yolo":
        return YoloDetector(
            model_path=settings.YOLO_MODEL_PATH,
            class_map=settings.YOLO_CLASS_MAP,
        )
    return SimulatedDetector()
