"""
Vision bridge for FacePass FabLab.

Converts client-uploaded images into face-analysis results using the
FaceEngine, with lazy singleton initialization so the heavy InsightFace
models load only on first use (and the API can boot without them).

Implements §9 Detailed AI Pipeline steps 1-5 for HTTP-delivered frames.
"""

import base64
import binascii
import logging
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from app.config import BASE_DIR

logger = logging.getLogger(__name__)

_ENGINE = None
_ENGINE_FAILED = False


class VisionUnavailableError(RuntimeError):
    """Raised when the CV engine cannot be initialized (e.g. missing models)."""


def engine_state() -> str:
    """
    Report engine status WITHOUT initializing anything.
    'not_loaded' | 'ready' | 'failed' — safe for health probes.
    """
    if _ENGINE is not None:
        return 'ready'
    if _ENGINE_FAILED:
        return 'failed'
    return 'not_loaded'


def get_engine():
    """Return the shared FaceEngine singleton, initializing lazily."""
    global _ENGINE, _ENGINE_FAILED
    if _ENGINE is not None:
        return _ENGINE
    if _ENGINE_FAILED:
        raise VisionUnavailableError(
            "Face engine failed to initialize earlier "
            "(InsightFace models missing or invalid)."
        )
    try:
        from app.face_engine import FaceEngine
        _ENGINE = FaceEngine()
        logger.info("FaceEngine initialized")
        return _ENGINE
    except Exception as exc:  # pragma: no cover - depends on model download
        _ENGINE_FAILED = True
        logger.error("FaceEngine init failed: %s", exc)
        raise VisionUnavailableError(str(exc)) from exc


def decode_image(data: str) -> np.ndarray:
    """
    Decode an image from a base64 string (raw or data-URI prefixed)
    or a raw byte string into a BGR numpy array.

    Raises ValueError on undecodable input.
    """
    if not data or not isinstance(data, str):
        raise ValueError("Empty image payload")

    payload = data.strip()
    if payload.startswith("data:"):
        # data:image/jpeg;base64,xxxx
        _, _, payload = payload.partition(",")

    try:
        img_bytes = base64.b64decode(payload, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Image is not valid base64") from exc

    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Could not decode image bytes")
    return frame


def analyze_frame(frame: np.ndarray) -> dict:
    """
    Run the full pipeline on one frame: detect -> quality -> embed.

    Returns dict with:
      - face_count, quality_passed, quality_reasons
      - embedding (normalized np.ndarray or None)
      - landmarks (kps), bbox
      - latency_ms
    """
    engine = get_engine()
    t0 = time.perf_counter()

    detected = engine.detect_faces(frame)
    latency_ms = round((time.perf_counter() - t0) * 1000, 1)

    result = {
        "face_count": len(detected),
        "quality_passed": False,
        "quality_reasons": [],
        "embedding": None,
        "landmarks": None,
        "bbox": None,
        "latency_ms": latency_ms,
    }

    if not detected:
        return result

    # Largest face = closest to camera (§9.2 multiple-face rule)
    best = max(detected, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

    passed, reasons = engine.quality_check(best, frame)
    result["quality_passed"] = passed
    result["quality_reasons"] = reasons
    result["embedding"] = engine.extract_embedding(best)
    result["landmarks"] = getattr(best, "kps", None)
    result["bbox"] = best.bbox.astype(int).tolist()
    result["_face_obj"] = best  # consumed in-process, never serialized
    return result


def analyze_frames(frames: list) -> dict:
    """Analyze a list of frames, returning per-frame results plus aggregates."""
    results = [analyze_frame(f) for f in frames]
    usable = [r for r in results if r["face_count"] > 0]
    return {
        "frames": results,
        "frames_with_face": len(usable),
        "max_face_count": max((r["face_count"] for r in results), default=0),
    }


def save_evidence(frame: np.ndarray, kind: str = "logs") -> str:
    """
    Persist a frame under images/<kind>/YYYY-MM-DD/ and return its path.
    kind: 'logs' | 'alerts' | 'enrolled'
    """
    day = datetime.now().strftime("%Y-%m-%d")
    out_dir = BASE_DIR / "images" / kind / day
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{int(time.time() * 1000)}.jpg"
    path = out_dir / filename
    cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    rel = Path("images") / kind / day / filename
    return str(rel)


def frames_from_payloads(payloads: list) -> list:
    """Decode a list of base64 payloads, skipping invalid entries."""
    frames = []
    errors = 0
    for p in payloads or []:
        try:
            frames.append(decode_image(p))
        except ValueError:
            errors += 1
    return frames, errors
