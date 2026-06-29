"""
client.py — HTTP Client giao tiếp giữa Jetson và FastAPI Server (PC)
════════════════════════════════════════════════════════════════════
  - load_embeddings(session_id) → Pull danh sách embedding từ server
  - send_attendance(payload)    → Gửi kết quả điểm danh về server
  - send_device_stats(stats)    → Gửi GPU stats về server (monitoring)
"""

import logging
from typing import Optional

import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import SERVER_URL, INTERNAL_API_KEY

logger = logging.getLogger("jetson_client")

HEADERS = {
    "X-Internal-Api-Key": INTERNAL_API_KEY,
    "Content-Type":       "application/json",
}


def _make_session() -> requests.Session:
    """Tạo requests.Session với retry tự động (không retry POST để tránh duplicate)."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[502, 503, 504],
        allowed_methods=["GET"],   # Chỉ auto-retry GET, POST do pipeline tự retry
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class JetsonClient:
    """HTTP Client singleton để giao tiếp với FastAPI Gateway trên PC."""

    def __init__(self):
        self._session = _make_session()
        self._base    = SERVER_URL.rstrip("/")
        logger.info(f"[JetsonClient] Server: {self._base}")

    def load_embeddings(self, session_id: str) -> dict:
        """
        GET /internal/embeddings?session_id=<uuid>
        Trả về dict { student_id: { full_name, student_code, embedding: np.ndarray } }
        """
        url = f"{self._base}/internal/embeddings"
        logger.info(f"[Client] GET {url}?session_id={session_id}")

        resp = self._session.get(
            url,
            params={"session_id": session_id},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()  # List[{student_id, full_name, student_code, embedding: [float...]}]

        registered = {}
        for item in data:
            emb = np.array(item["embedding"], dtype=np.float32)
            # Chuẩn hóa L2 phòng khi server chưa normalize
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            registered[item["student_id"]] = {
                "full_name":    item.get("full_name",    "N/A"),
                "student_code": item.get("student_code", "N/A"),
                "research_id":  item.get("research_id",  ""),
                "embedding":    emb,
            }

        logger.info(f"[Client] Đã tải {len(registered)} embeddings từ server.")
        return registered

    def send_attendance(self, payload: dict) -> bool:
        """
        POST /internal/attendance/mark
        payload = {
            session_id, student_id, confidence, detected_at, source, device_info
        }
        Trả về True nếu server xác nhận thành công.
        """
        url = f"{self._base}/internal/attendance/mark"
        try:
            resp = self._session.post(url, json=payload, headers=HEADERS, timeout=8)
            if resp.status_code == 200:
                return True
            logger.warning(
                f"[Client] Server từ chối mark attendance: "
                f"HTTP {resp.status_code} — {resp.text[:200]}"
            )
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"[Client] Lỗi kết nối server: {e}")
            return False

    def send_device_stats(self, stats_dict: dict) -> bool:
        """
        POST /internal/device-stats
        Gửi thông số GPU (nhiệt độ, VRAM, % load) về server để monitoring.
        Endpoint này là tùy chọn — server có thể không implement.
        """
        url = f"{self._base}/internal/device-stats"
        try:
            resp = self._session.post(url, json=stats_dict, headers=HEADERS, timeout=5)
            return resp.status_code == 200
        except requests.exceptions.RequestException:
            return False  # Không log lỗi vì endpoint này là optional

    def health_check(self) -> bool:
        """Kiểm tra xem server có đang chạy không."""
        url = f"{self._base}/health"
        try:
            resp = self._session.get(url, timeout=5)
            ok = resp.status_code == 200
            if ok:
                logger.info("[Client] Server health check: OK")
            else:
                logger.warning(f"[Client] Server health check: HTTP {resp.status_code}")
            return ok
        except requests.exceptions.RequestException as e:
            logger.error(f"[Client] Server không phản hồi: {e}")
            return False
