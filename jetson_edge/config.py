"""
config.py — Cấu hình Jetson Edge Agent (đọc từ .env)
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Server ───────────────────────────────────────────────────────
SERVER_URL        = os.getenv("SERVER_URL",       "http://192.168.1.100:8000")
INTERNAL_API_KEY  = os.getenv("INTERNAL_API_KEY", "change-me-in-dotenv")

# ── Camera ───────────────────────────────────────────────────────
CAMERA_INDEX      = int(os.getenv("CAMERA_INDEX", "0"))

# ── AI Thresholds ─────────────────────────────────────────────────
SIMILARITY_THRESHOLD   = float(os.getenv("SIMILARITY_THRESHOLD",  "0.65"))
SNAPSHOT_COOLDOWN      = float(os.getenv("SNAPSHOT_COOLDOWN",     "3.0"))
LIVENESS_MAD_THRESHOLD = float(os.getenv("LIVENESS_MAD_THRESHOLD","1.4"))
LIVENESS_FRAME_COUNT   = int(os.getenv("LIVENESS_FRAME_COUNT",    "3"))
LIVENESS_FRAME_DELAY   = float(os.getenv("LIVENESS_FRAME_DELAY",  "0.12"))

# ── GPU Monitoring ────────────────────────────────────────────────
GPU_LOG_INTERVAL  = float(os.getenv("GPU_LOG_INTERVAL", "30.0"))  # giây
GPU_WARN_TEMP_C   = float(os.getenv("GPU_WARN_TEMP_C",  "80.0"))  # °C

# ── Retry Queue ───────────────────────────────────────────────────
RETRY_QUEUE_MAX   = int(os.getenv("RETRY_QUEUE_MAX", "100"))
