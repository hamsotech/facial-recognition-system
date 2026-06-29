"""
shared/similarity_service.py
═════════════════════════════
Gộp từ 4 bản trong:
  - service_arcface/similarity_service.py    (dùng scipy)
  - service_facenet/similarity_service.py    (dùng numpy + hỗ trợ Tensor)
  - service_mobilefacenet/similarity_service.py (dùng numpy đơn giản)
  - services_dlib/similarity_service.py      (dùng numpy đơn giản)

Bản hợp nhất:
  - Thuần numpy (không phụ thuộc scipy)
  - Hỗ trợ cả torch.Tensor lẫn np.ndarray (từ bản facenet)
  - Tính bằng dot product thủ công thay vì scipy distance (nhanh hơn)
"""

import logging
from typing import Union

import numpy as np
import torch

logger = logging.getLogger(__name__)


def cosine_similarity(
    emb1: Union[np.ndarray, "torch.Tensor"],
    emb2: Union[np.ndarray, "torch.Tensor"],
) -> float:
    """
    Tính Cosine Similarity giữa hai vector đặc trưng.
    Chấp nhận cả PyTorch Tensor và NumPy ndarray.

    Args:
        emb1: Vector 1 (bất kỳ chiều nào, sẽ được flatten).
        emb2: Vector 2 (bất kỳ chiều nào, sẽ được flatten).

    Returns:
        Giá trị float trong khoảng [-1.0, 1.0].
        1.0 = giống nhau hoàn toàn, -1.0 = trái ngược.
    """
    # Chuyển Tensor → numpy nếu cần
    if isinstance(emb1, torch.Tensor):
        emb1 = emb1.detach().cpu().numpy()
    if isinstance(emb2, torch.Tensor):
        emb2 = emb2.detach().cpu().numpy()

    v1 = np.array(emb1, dtype=np.float32).flatten()
    v2 = np.array(emb2, dtype=np.float32).flatten()

    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)

    if norm1 == 0.0 or norm2 == 0.0:
        logger.warning("[Similarity] Một trong hai vector có norm = 0.")
        return 0.0

    return float(np.dot(v1, v2) / (norm1 * norm2))
