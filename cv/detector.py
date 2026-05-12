"""
YOLOv11 ONNX beach crowd detector.

Loads a YOLOv11 model exported to ONNX and detects people on beach
images to estimate occupancy levels. Designed to run on Windows with
onnxruntime-directml for AMD GPU acceleration.

Falls back to simulated detections when no ONNX model is available.
"""

from __future__ import annotations

import io
import logging
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger("neptuno.cv.detector")

MODEL_PATH = Path(__file__).parent / "yolov11n.onnx"
INPUT_SIZE = (640, 640)
PERSON_CLASS_ID = 0
CONFIDENCE_THRESHOLD = 0.45
NMS_THRESHOLD = 0.5


@dataclass
class Detection:
    """A single detection bounding box."""

    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int


@dataclass
class OccupancyResult:
    """Beach occupancy estimation result."""

    person_count: int
    occupation_rate: str
    detections: list[Detection]
    is_simulated: bool


def load_onnx_session():
    """Load the ONNX model with available execution providers."""
    try:
        import onnxruntime as ort

        if not MODEL_PATH.exists():
            logger.warning("ONNX model not found at %s", MODEL_PATH)
            return None

        providers = ort.get_available_providers()
        preferred = []
        if "DmlExecutionProvider" in providers:
            preferred.append("DmlExecutionProvider")
        preferred.append("CPUExecutionProvider")

        session = ort.InferenceSession(str(MODEL_PATH), providers=preferred)
        logger.info("ONNX model loaded with providers: %s", preferred)
        return session
    except Exception as exc:
        logger.warning("Failed to load ONNX model: %s", exc)
        return None


def preprocess_image(image: Image.Image) -> np.ndarray:
    """Resize and normalize image for YOLOv11 input."""
    img = image.resize(INPUT_SIZE)
    arr = np.array(img).astype(np.float32) / 255.0
    # HWC -> CHW
    arr = arr.transpose(2, 0, 1)
    # Add batch dimension -> BCHW
    arr = np.expand_dims(arr, axis=0)
    return arr


def postprocess_detections(
    output: np.ndarray,
    original_width: int,
    original_height: int,
) -> list[Detection]:
    """Parse YOLO output tensor into Detection objects."""
    detections: list[Detection] = []

    # YOLOv11 output shape: (1, num_detections, 6) or (1, 84, 8400)
    if output.ndim == 3:
        if output.shape[1] == 84:
            # Transposed format: (1, 84, N_detections) -> (1, N, 84)
            output = output.transpose(0, 2, 1)
        preds = output[0]
    else:
        preds = output

    scale_x = original_width / INPUT_SIZE[0]
    scale_y = original_height / INPUT_SIZE[1]

    for pred in preds:
        if len(pred) >= 6:
            # Direct format: x1, y1, x2, y2, conf, class
            conf = float(pred[4])
            class_id = int(pred[5])
        elif len(pred) >= 5:
            # cx, cy, w, h, class_scores...
            class_scores = pred[4:]
            class_id = int(np.argmax(class_scores))
            conf = float(class_scores[class_id])
        else:
            continue

        if conf < CONFIDENCE_THRESHOLD:
            continue
        if class_id != PERSON_CLASS_ID:
            continue

        cx, cy, w, h = pred[0], pred[1], pred[2], pred[3]
        x1 = (cx - w / 2) * scale_x
        y1 = (cy - h / 2) * scale_y
        x2 = (cx + w / 2) * scale_x
        y2 = (cy + h / 2) * scale_y

        detections.append(Detection(
            x1=float(x1), y1=float(y1),
            x2=float(x2), y2=float(y2),
            confidence=conf, class_id=class_id,
        ))

    # Simple NMS
    detections = _nms(detections)
    return detections


def _nms(dets: list[Detection]) -> list[Detection]:
    """Non-maximum suppression."""
    if not dets:
        return []

    dets.sort(key=lambda d: d.confidence, reverse=True)
    keep: list[Detection] = []

    for det in dets:
        is_duplicate = False
        for kept in keep:
            iou = _iou(det, kept)
            if iou > NMS_THRESHOLD:
                is_duplicate = True
                break
        if not is_duplicate:
            keep.append(det)

    return keep


def _iou(a: Detection, b: Detection) -> float:
    """Intersection over Union of two boxes."""
    x1 = max(a.x1, b.x1)
    y1 = max(a.y1, b.y1)
    x2 = min(a.x2, b.x2)
    y2 = min(a.y2, b.y2)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (a.x2 - a.x1) * (a.y2 - a.y1)
    area_b = (b.x2 - b.x1) * (b.y2 - b.y1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0


def classify_occupation(count: int) -> str:
    """Map person count to occupation rate category."""
    if count <= 5:
        return "low"
    elif count <= 20:
        return "medium"
    elif count <= 50:
        return "high"
    return "veryHigh"


def detect_occupancy(image_path: str | Path | None = None) -> OccupancyResult:
    """Detect beach occupancy from an image.

    If no ONNX model is available or no image is provided, returns
    a simulated result.
    """
    session = load_onnx_session()

    if session is None or image_path is None:
        import random

        count = random.randint(0, 60)
        logger.info("SIMULATED occupancy detection: %d people", count)
        return OccupancyResult(
            person_count=count,
            occupation_rate=classify_occupation(count),
            detections=[],
            is_simulated=True,
        )

    try:
        img = Image.open(image_path).convert("RGB")
        input_tensor = preprocess_image(img)

        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: input_tensor})
        output = outputs[0]

        dets = postprocess_detections(output, img.width, img.height)
        count = len(dets)

        logger.info("REAL occupancy detection: %d people from %s", count, image_path)
        return OccupancyResult(
            person_count=count,
            occupation_rate=classify_occupation(count),
            detections=dets,
            is_simulated=False,
        )
    except Exception as exc:
        logger.error("Detection failed: %s", exc)
        return OccupancyResult(
            person_count=0,
            occupation_rate="low",
            detections=[],
            is_simulated=True,
        )


def detect_occupancy_from_url(snapshot_url: str) -> OccupancyResult:
    """Fetch a Windy webcam snapshot and run occupancy detection on it.

    Downloads the image into memory (no disk I/O) and passes it to
    detect_occupancy. Falls back to simulation if download fails.
    """
    try:
        req = urllib.request.Request(
            snapshot_url,
            headers={"User-Agent": "NEPTUNO-SmartBeach/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            img_bytes = resp.read()

        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        session = load_onnx_session()

        if session is None:
            import random
            count = random.randint(0, 60)
            logger.info("SIMULATED (no model) from URL %s: %d people", snapshot_url, count)
            return OccupancyResult(
                person_count=count,
                occupation_rate=classify_occupation(count),
                detections=[],
                is_simulated=True,
            )

        input_tensor = preprocess_image(img)
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: input_tensor})
        dets = postprocess_detections(outputs[0], img.width, img.height)
        count = len(dets)
        logger.info("REAL detection from Windy snapshot: %d people", count)
        return OccupancyResult(
            person_count=count,
            occupation_rate=classify_occupation(count),
            detections=dets,
            is_simulated=False,
        )
    except Exception as exc:
        logger.warning("Webcam detection failed (%s), falling back to simulation", exc)
        import random
        count = random.randint(0, 60)
        return OccupancyResult(
            person_count=count,
            occupation_rate=classify_occupation(count),
            detections=[],
            is_simulated=True,
        )
