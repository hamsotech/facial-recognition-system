"""
shared/__init__.py
Xuất các shared service để import ngắn gọn:

    from app.shared import detect_person, crop_person, align_face
    from app.shared import cosine_similarity, mark_attendance
"""

from .yolo_detector    import detect_person, crop_person
from .mtcnn_alignment  import align_face
from .similarity_service import cosine_similarity
from .attendance_service import mark_attendance

__all__ = [
    "detect_person",
    "crop_person",
    "align_face",
    "cosine_similarity",
    "mark_attendance",
]
