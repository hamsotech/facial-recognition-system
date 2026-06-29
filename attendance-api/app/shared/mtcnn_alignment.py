"""
shared/mtcnn_alignment.py
══════════════════════════
Gộp từ 3 bản trong:
  - service_arcface/mtcnn_alignment.py   (dùng torch.cuda, không có PIL)
  - service_facenet/mtcnn_alignment.py   (dùng PIL.Image)
  - service_mobilefacenet/mtcnn_alignment.py (có device + thresholds tốt hơn)

Bản hợp nhất:
  - Tự detect CUDA và gán device
  - Dùng thresholds [0.6, 0.7, 0.7] chuẩn (từ bản arcface/mobilefacenet)
  - Không cần PIL — convert trực tiếp bằng cv2
"""

import logging

import cv2
import torch
from facenet_pytorch import MTCNN

logger = logging.getLogger(__name__)

_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"[MTCNN] Device: {_device}")

_mtcnn = MTCNN(
    image_size=160,
    margin=0,
    min_face_size=20,
    thresholds=[0.6, 0.7, 0.7],
    factor=0.709,
    post_process=True,
    device=_device,
    keep_all=False,
)


def align_face(person_image) -> torch.Tensor | None:
    """
    Phát hiện và căn chỉnh khuôn mặt từ ROI người bằng MTCNN.

    Args:
        person_image: numpy array BGR (đầu ra của crop_person).

    Returns:
        Tensor shape [3, 160, 160] đã normalize, hoặc None nếu không tìm thấy mặt.
    """
    if person_image is None or person_image.size == 0:
        return None
    try:
        rgb = cv2.cvtColor(person_image, cv2.COLOR_BGR2RGB)
        face_tensor = _mtcnn(rgb)
        return face_tensor
    except Exception as e:
        logger.debug(f"[MTCNN] Lỗi căn chỉnh khuôn mặt: {e}")
        return None
