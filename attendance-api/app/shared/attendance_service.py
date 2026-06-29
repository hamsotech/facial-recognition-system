"""
shared/attendance_service.py
════════════════════════════
Gộp từ 3 bản giống nhau trong:
  - service_arcface/attendance_service.py
  - service_facenet/attendance_service.py
  - service_mobilefacenet/attendance_service.py
  - services_dlib/attendance_service.py

Dùng chung cho tất cả service nhận diện.
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("SPRING_URL", "http://localhost:8080")
_ENDPOINT   = f"{BACKEND_URL}/api/attendance"


def mark_attendance(student_id: str, session_id: str, confidence_score: float) -> bool:
    """
    Gọi REST API Spring Boot để lưu kết quả điểm danh xuống PostgreSQL.

    Args:
        student_id:       UUID sinh viên
        session_id:       UUID phiên học
        confidence_score: Độ tương đồng cosine [0.0 – 1.0]

    Returns:
        True nếu server phản hồi HTTP 200, False nếu lỗi.
    """
    payload = {
        "studentId":  student_id,
        "sessionId":  session_id,
        "confidence": round(float(confidence_score), 6),
    }
    try:
        resp = requests.post(_ENDPOINT, json=payload, timeout=8)
        if resp.status_code == 200:
            return True
        logger.warning(
            f"[AttendanceService] Backend từ chối: HTTP {resp.status_code} — {resp.text[:200]}"
        )
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"[AttendanceService] Lỗi kết nối Backend: {e}")
        return False
