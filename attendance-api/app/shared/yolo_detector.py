"""
shared/yolo_detector.py
════════════════════════
Gộp từ 3 bản trong:
  - service_arcface/yolo_detector.py   (có margin 10%)
  - service_facenet/yolo_detector.py   (không có margin)
  - service_mobilefacenet/yolo_detector.py

Bản hợp nhất:
  - Giữ bảo vệ input (chặn str, chỉ chấp nhận np.ndarray)
  - Thêm margin crop từ bản arcface (chuẩn hơn)
  - Đọc đường dẫn model từ biến môi trường YOLO_MODEL_PATH
"""

import os
import logging

import cv2
import numpy as np
from ultralytics import YOLO

logger = logging.getLogger(__name__)

_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
_model: YOLO | None = None


def _get_model() -> YOLO:
    """Lazy-load YOLO model (tải một lần, dùng nhiều lần)."""
    global _model
    if _model is None:
        logger.info(f"[YOLO] Đang tải model từ: {_MODEL_PATH}")
        _model = YOLO(_MODEL_PATH)
    return _model


def detect_person(frame: np.ndarray, conf: float = 0.5) -> list[dict]:
    """
    Phát hiện người trong frame camera.

    Args:
        frame: numpy array BGR từ cv2.VideoCapture — KHÔNG chấp nhận đường dẫn ảnh.
        conf:  Ngưỡng confidence của YOLO (mặc định 0.5).

    Returns:
        List các dict {"x1", "y1", "x2", "y2"} của từng người phát hiện được.

    Raises:
        ValueError: Nếu đầu vào không phải numpy array (bảo vệ chống ảnh tĩnh).
    """
    if not isinstance(frame, np.ndarray):
        raise ValueError(
            "[Bảo mật] Chỉ chấp nhận hình ảnh trực tiếp từ camera (numpy array). "
            "Không hỗ trợ đường dẫn ảnh tĩnh."
        )

    image = frame.copy()
    results = _get_model().predict(source=image, conf=conf, verbose=False)
    del image

    persons = []
    for result in results:
        for box in result.boxes:
            if int(box.cls[0]) != 0:   # class 0 = person
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            persons.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})

    return persons


def crop_person(image: np.ndarray, person: dict, margin: float = 0.10) -> np.ndarray:
    """
    Cắt vùng ROI của người, nới thêm margin để không cắt mất mặt/tóc/cằm.

    Args:
        image:  Frame gốc BGR.
        person: Dict {"x1", "y1", "x2", "y2"} từ detect_person().
        margin: Tỷ lệ mở rộng box (mặc định 10%).

    Returns:
        Ảnh numpy array BGR đã cắt.
    """
    h, w = image.shape[:2]
    x1, y1, x2, y2 = person["x1"], person["y1"], person["x2"], person["y2"]
    bw, bh = x2 - x1, y2 - y1

    x1 = max(0, int(x1 - bw * margin))
    y1 = max(0, int(y1 - bh * margin))
    x2 = min(w, int(x2 + bw * margin))
    y2 = min(h, int(y2 + bh * margin))

    return image[y1:y2, x1:x2]
