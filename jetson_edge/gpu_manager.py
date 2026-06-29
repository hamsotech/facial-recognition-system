"""
gpu_manager.py — Quản lý và kiểm tra GPU/CUDA trên Jetson Orin/Nano
═══════════════════════════════════════════════════════════════════════
Chức năng:
  - Phát hiện GPU (CUDA) có sẵn hay không
  - Đọc thông tin GPU: tên, VRAM, nhiệt độ, % sử dụng
  - Trên Jetson: dùng jtop (jetson-stats) để đọc thông tin chi tiết hơn
  - Trên máy thường: dùng nvidia-smi / torch.cuda
  - Cung cấp DeviceManager singleton dùng chung cho toàn bộ pipeline
"""

import os
import subprocess
import platform
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

import torch
import numpy as np

logger = logging.getLogger("gpu_manager")

# ══════════════════════════════════════════════════════════════════
# DATA CLASS — Thông tin GPU tại một thời điểm
# ══════════════════════════════════════════════════════════════════
@dataclass
class GPUStats:
    available:        bool    = False
    device_name:      str     = "CPU"
    cuda_version:     str     = "N/A"
    driver_version:   str     = "N/A"
    total_vram_mb:    float   = 0.0
    used_vram_mb:     float   = 0.0
    free_vram_mb:     float   = 0.0
    vram_usage_pct:   float   = 0.0
    gpu_util_pct:     float   = 0.0    # % tác vụ AI đang dùng GPU
    gpu_temp_c:       float   = 0.0    # Nhiệt độ GPU (°C)
    power_draw_w:     float   = 0.0    # Công suất hiện tại (W)
    power_limit_w:    float   = 0.0    # Giới hạn công suất (W)
    is_jetson:        bool    = False
    jetson_model:     str     = "N/A"
    torch_device:     str     = "cpu"


# ══════════════════════════════════════════════════════════════════
# PHÁT HIỆN JETSON
# ══════════════════════════════════════════════════════════════════
def _detect_jetson() -> tuple[bool, str]:
    """
    Kiểm tra xem thiết bị có phải Jetson không bằng cách đọc
    /proc/device-tree/model (chỉ có trên ARM/Jetson).
    """
    model_path = "/proc/device-tree/model"
    if os.path.exists(model_path):
        try:
            with open(model_path, "r", errors="ignore") as f:
                model_str = f.read().strip().rstrip("\x00")
            if "jetson" in model_str.lower() or "nvidia" in model_str.lower():
                return True, model_str
        except Exception:
            pass

    # Fallback: kiểm tra tegrastats
    if os.path.exists("/usr/bin/tegrastats"):
        return True, "NVIDIA Jetson (tegrastats detected)"

    return False, "N/A"


# ══════════════════════════════════════════════════════════════════
# ĐỌC THÔNG TIN GPU QUA nvidia-smi (Máy thường hoặc Jetson)
# ══════════════════════════════════════════════════════════════════
def _query_nvidia_smi() -> dict:
    """
    Chạy nvidia-smi và parse kết quả.
    Trả về dict hoặc {} nếu nvidia-smi không có.
    """
    query_fields = [
        "name",
        "driver_version",
        "memory.total",
        "memory.used",
        "memory.free",
        "utilization.gpu",
        "temperature.gpu",
        "power.draw",
        "power.limit",
    ]
    cmd = [
        "nvidia-smi",
        f"--query-gpu={','.join(query_fields)}",
        "--format=csv,noheader,nounits"
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return {}
        parts = [p.strip() for p in result.stdout.strip().split(",")]
        if len(parts) < len(query_fields):
            return {}

        def _float(val: str) -> float:
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        return {
            "device_name":     parts[0],
            "driver_version":  parts[1],
            "total_vram_mb":   _float(parts[2]),
            "used_vram_mb":    _float(parts[3]),
            "free_vram_mb":    _float(parts[4]),
            "gpu_util_pct":    _float(parts[5]),
            "gpu_temp_c":      _float(parts[6]),
            "power_draw_w":    _float(parts[7]),
            "power_limit_w":   _float(parts[8]),
        }
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}


# ══════════════════════════════════════════════════════════════════
# ĐỌC THÔNG TIN GPU QUA jtop (chỉ có trên Jetson)
# ══════════════════════════════════════════════════════════════════
def _query_jtop() -> dict:
    """
    Đọc thông tin Jetson qua thư viện jtop (jetson-stats).
    Chỉ hoạt động khi đã cài: pip install jetson-stats
    """
    try:
        from jtop import jtop
        stats = {}
        with jtop(interval=0.5) as jetson:
            if jetson.ok():
                gpu_info = jetson.gpu
                # gpu_info là dict hoặc list tuỳ phiên bản jtop
                if isinstance(gpu_info, dict):
                    # jtop >= 4.x
                    first_gpu = next(iter(gpu_info.values()), {})
                    stats["gpu_util_pct"] = float(first_gpu.get("status", {}).get("load", 0) or 0)
                    stats["gpu_temp_c"]   = float(first_gpu.get("temp", 0) or 0)
                elif isinstance(gpu_info, (int, float)):
                    stats["gpu_util_pct"] = float(gpu_info)

                # RAM Jetson là unified memory (CPU + GPU chia chung)
                ram = jetson.memory.get("RAM", {})
                stats["total_vram_mb"] = float(ram.get("tot", 0)) / 1024.0
                stats["used_vram_mb"]  = float(ram.get("used", 0)) / 1024.0
                stats["free_vram_mb"]  = stats["total_vram_mb"] - stats["used_vram_mb"]

                # Công suất
                power = jetson.power
                if isinstance(power, dict):
                    total_power = power.get("tot", {})
                    stats["power_draw_w"] = float(total_power.get("cur", 0) or 0) / 1000.0
        return stats
    except ImportError:
        logger.debug("jtop không được cài đặt, bỏ qua.")
        return {}
    except Exception as e:
        logger.debug(f"jtop lỗi: {e}")
        return {}


# ══════════════════════════════════════════════════════════════════
# LẤY THÔNG TIN GPU BẰNG TORCH (VRAM)
# ══════════════════════════════════════════════════════════════════
def _query_torch_cuda(device_idx: int = 0) -> dict:
    """
    Đọc thông tin VRAM qua torch.cuda — chính xác nhất vì dùng runtime PyTorch.
    """
    if not torch.cuda.is_available():
        return {}
    try:
        props        = torch.cuda.get_device_properties(device_idx)
        total_mb     = props.total_memory / (1024 ** 2)
        reserved_mb  = torch.cuda.memory_reserved(device_idx) / (1024 ** 2)
        allocated_mb = torch.cuda.memory_allocated(device_idx) / (1024 ** 2)
        free_mb      = total_mb - reserved_mb
        return {
            "device_name":   props.name,
            "total_vram_mb": total_mb,
            "used_vram_mb":  allocated_mb,
            "free_vram_mb":  free_mb,
            "cuda_version":  torch.version.cuda or "N/A",
            "compute_cap":   f"{props.major}.{props.minor}",
        }
    except Exception as e:
        logger.debug(f"torch.cuda query lỗi: {e}")
        return {}


# ══════════════════════════════════════════════════════════════════
# HÀM CHÍNH: get_gpu_stats()
# ══════════════════════════════════════════════════════════════════
def get_gpu_stats() -> GPUStats:
    """
    Tổng hợp thông tin GPU từ nhiều nguồn:
    1. torch.cuda   → VRAM chính xác
    2. nvidia-smi   → Nhiệt độ, % sử dụng, công suất
    3. jtop         → Thông tin Jetson unified memory (nếu có)
    """
    stats = GPUStats()
    is_jetson, jetson_model = _detect_jetson()
    stats.is_jetson   = is_jetson
    stats.jetson_model = jetson_model

    cuda_available = torch.cuda.is_available()
    stats.available = cuda_available

    if not cuda_available:
        stats.device_name  = "CPU only (CUDA không khả dụng)"
        stats.torch_device = "cpu"
        return stats

    stats.torch_device  = "cuda"
    stats.cuda_version  = torch.version.cuda or "N/A"

    # Nguồn 1: torch.cuda
    torch_info = _query_torch_cuda()
    if torch_info:
        stats.device_name   = torch_info.get("device_name", stats.device_name)
        stats.total_vram_mb = torch_info.get("total_vram_mb", 0.0)
        stats.used_vram_mb  = torch_info.get("used_vram_mb", 0.0)
        stats.free_vram_mb  = torch_info.get("free_vram_mb", 0.0)
        stats.cuda_version  = torch_info.get("cuda_version", stats.cuda_version)

    # Nguồn 2: nvidia-smi (ưu tiên % GPU và nhiệt độ từ đây)
    smi_info = _query_nvidia_smi()
    if smi_info:
        stats.device_name    = smi_info.get("device_name", stats.device_name)
        stats.driver_version = smi_info.get("driver_version", "N/A")
        stats.gpu_util_pct   = smi_info.get("gpu_util_pct", 0.0)
        stats.gpu_temp_c     = smi_info.get("gpu_temp_c", 0.0)
        stats.power_draw_w   = smi_info.get("power_draw_w", 0.0)
        stats.power_limit_w  = smi_info.get("power_limit_w", 0.0)
        # Nếu torch không có VRAM thì lấy từ smi
        if stats.total_vram_mb == 0:
            stats.total_vram_mb = smi_info.get("total_vram_mb", 0.0)
            stats.used_vram_mb  = smi_info.get("used_vram_mb", 0.0)
            stats.free_vram_mb  = smi_info.get("free_vram_mb", 0.0)

    # Nguồn 3: jtop (ghi đè nếu là Jetson vì unified memory chính xác hơn)
    if is_jetson:
        jtop_info = _query_jtop()
        if jtop_info:
            stats.total_vram_mb = jtop_info.get("total_vram_mb", stats.total_vram_mb)
            stats.used_vram_mb  = jtop_info.get("used_vram_mb", stats.used_vram_mb)
            stats.free_vram_mb  = jtop_info.get("free_vram_mb", stats.free_vram_mb)
            stats.gpu_util_pct  = jtop_info.get("gpu_util_pct", stats.gpu_util_pct)
            stats.gpu_temp_c    = jtop_info.get("gpu_temp_c", stats.gpu_temp_c)
            stats.power_draw_w  = jtop_info.get("power_draw_w", stats.power_draw_w)

    # Tính % VRAM sử dụng
    if stats.total_vram_mb > 0:
        stats.vram_usage_pct = (stats.used_vram_mb / stats.total_vram_mb) * 100.0

    return stats


# ══════════════════════════════════════════════════════════════════
# IN BÁO CÁO GPU RA TERMINAL (KHI KHỞI ĐỘNG)
# ══════════════════════════════════════════════════════════════════
def print_gpu_report(stats: GPUStats | None = None):
    """In báo cáo GPU chi tiết ra terminal khi hệ thống khởi động."""
    if stats is None:
        stats = get_gpu_stats()

    banner = "═" * 58
    print(f"\n{banner}")
    print("  🖥️  BÁO CÁO THIẾT BỊ AI")
    print(banner)

    if stats.is_jetson:
        print(f"  🤖 Thiết bị   : NVIDIA Jetson — {stats.jetson_model}")
    else:
        print(f"  💻 Thiết bị   : {platform.node()} ({platform.system()})")

    if stats.available:
        print(f"  ✅ GPU        : {stats.device_name}")
        print(f"  🔧 CUDA       : {stats.cuda_version}  |  Driver: {stats.driver_version}")
        print(f"  🧠 VRAM       : {stats.used_vram_mb:.0f} MB / {stats.total_vram_mb:.0f} MB  "
              f"({stats.vram_usage_pct:.1f}% đã dùng)")
        print(f"  📊 GPU Load   : {stats.gpu_util_pct:.1f}%")
        print(f"  🌡️  Nhiệt độ  : {stats.gpu_temp_c:.1f} °C")
        if stats.power_draw_w > 0:
            print(f"  ⚡ Công suất  : {stats.power_draw_w:.1f} W / {stats.power_limit_w:.1f} W")
        print(f"  🚀 PyTorch    : {torch.__version__}  |  Device: {stats.torch_device}")
    else:
        print("  ❌ CUDA không khả dụng — Chạy trên CPU")
        print(f"  🐢 PyTorch    : {torch.__version__}  |  Device: cpu")
        print("  ⚠️  Cảnh báo: Pipeline AI sẽ chạy chậm hơn đáng kể trên CPU!")

    print(f"{banner}\n")


# ══════════════════════════════════════════════════════════════════
# DEVICE MANAGER — Singleton dùng chung cho toàn bộ pipeline
# ══════════════════════════════════════════════════════════════════
class DeviceManager:
    """
    Singleton quản lý device (GPU/CPU) cho toàn bộ pipeline.
    Cung cấp:
      - .device      → torch.device để gán model/tensor
      - .ort_providers → List providers cho ONNX Runtime
      - .stats       → GPUStats hiện tại
      - .refresh()   → Cập nhật stats mới nhất
    """
    _instance: Optional["DeviceManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._stats: GPUStats = get_gpu_stats()
        self._last_refresh: float = time.time()

        if self._stats.available:
            self.device = torch.device("cuda")
            self.ort_providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            logger.info(f"[DeviceManager] Sử dụng GPU: {self._stats.device_name}")
        else:
            self.device = torch.device("cpu")
            self.ort_providers = ["CPUExecutionProvider"]
            logger.warning("[DeviceManager] CUDA không khả dụng. Chạy trên CPU.")

    @property
    def stats(self) -> GPUStats:
        return self._stats

    def refresh(self, force: bool = False) -> GPUStats:
        """
        Cập nhật GPU stats.
        Tự động throttle: chỉ refresh thực sự nếu đã qua 5 giây.
        """
        now = time.time()
        if force or (now - self._last_refresh) >= 5.0:
            self._stats = get_gpu_stats()
            self._last_refresh = now
        return self._stats

    def log_stats(self):
        """In thông số GPU ngắn gọn vào logger (dùng trong vòng lặp chính)."""
        s = self.refresh()
        if s.available:
            logger.debug(
                f"GPU: {s.gpu_util_pct:.0f}% | "
                f"VRAM: {s.used_vram_mb:.0f}/{s.total_vram_mb:.0f} MB | "
                f"Temp: {s.gpu_temp_c:.0f}°C | "
                f"Power: {s.power_draw_w:.1f}W"
            )

    def warn_if_hot(self, threshold_c: float = 80.0):
        """Cảnh báo khi GPU quá nhiệt."""
        s = self.refresh()
        if s.available and s.gpu_temp_c >= threshold_c:
            logger.warning(
                f"⚠️  GPU QUÁ NHIỆT: {s.gpu_temp_c:.1f}°C >= {threshold_c}°C! "
                "Hãy kiểm tra hệ thống tản nhiệt Jetson."
            )

    def to_dict(self) -> dict:
        """Chuyển stats hiện tại thành dict để gửi về server."""
        s = self.refresh()
        return {
            "available":      s.available,
            "device_name":    s.device_name,
            "cuda_version":   s.cuda_version,
            "total_vram_mb":  round(s.total_vram_mb, 1),
            "used_vram_mb":   round(s.used_vram_mb, 1),
            "vram_usage_pct": round(s.vram_usage_pct, 1),
            "gpu_util_pct":   round(s.gpu_util_pct, 1),
            "gpu_temp_c":     round(s.gpu_temp_c, 1),
            "power_draw_w":   round(s.power_draw_w, 1),
            "is_jetson":      s.is_jetson,
            "jetson_model":   s.jetson_model,
        }


# ══════════════════════════════════════════════════════════════════
# CHẠY TRỰC TIẾP ĐỂ KIỂM TRA
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.DEBUG)

    print("🔍 Đang kiểm tra GPU...")
    gpu_stats = get_gpu_stats()
    print_gpu_report(gpu_stats)

    dm = DeviceManager()
    print("📦 DeviceManager dict:")
    print(json.dumps(dm.to_dict(), indent=2, ensure_ascii=False))

    print(f"\n🔥 Torch device: {dm.device}")
    print(f"⚙️  ONNX providers: {dm.ort_providers}")
