"""
pipeline.py — AI Pipeline chạy trên Jetson (Edge Device)
══════════════════════════════════════════════════════════
Luồng xử lý:
  Camera → YOLO (GPU) → MTCNN (GPU) → FaceNet/ArcFace (GPU)
         → Cosine Similarity → HTTP POST về PC Server

Đặc điểm:
  - Toàn bộ model chạy trên GPU (CUDA) nếu có
  - Không dùng cv2.imshow() — Jetson không có màn hình
  - Không kết nối DB trực tiếp — giao tiếp qua HTTP REST
  - Liveness check chống ảnh tĩnh (giữ nguyên logic cũ)
  - Retry queue khi mất kết nối server
  - Log GPU stats mỗi 30 giây
"""

import os
import sys
import time
import logging
import threading
import queue
from datetime import datetime, timezone
from typing import Optional

import cv2
import numpy as np
import torch

from gpu_manager import DeviceManager, print_gpu_report
from client import JetsonClient

logger = logging.getLogger("jetson_pipeline")

# ══════════════════════════════════════════════════════════════════
# CẤU HÌNH (đọc từ .env qua config.py)
# ══════════════════════════════════════════════════════════════════
from config import (
    CAMERA_INDEX,
    SIMILARITY_THRESHOLD,
    SNAPSHOT_COOLDOWN,
    LIVENESS_MAD_THRESHOLD,
    LIVENESS_FRAME_COUNT,
    LIVENESS_FRAME_DELAY,
    GPU_LOG_INTERVAL,
    GPU_WARN_TEMP_C,
    RETRY_QUEUE_MAX,
)


# ══════════════════════════════════════════════════════════════════
# TẢI MODEL AI VỚI GPU
# ══════════════════════════════════════════════════════════════════
def load_ai_models(dm: DeviceManager):
    """
    Tải tất cả model AI lên GPU (nếu có CUDA).
    Trả về dict chứa các model đã sẵn sàng.
    """
    logger.info(f"[Models] Đang tải model AI lên {dm.device}...")

    # 1. YOLO — Phát hiện người
    from ultralytics import YOLO
    yolo_path = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
    yolo = YOLO(yolo_path)
    if dm.stats.available:
        # Ultralytics tự chọn device qua tham số predict(device=...)
        yolo_device = "cuda"
    else:
        yolo_device = "cpu"
    logger.info(f"[Models] YOLO loaded → device={yolo_device}")

    # 2. MTCNN — Căn chỉnh khuôn mặt
    from facenet_pytorch import MTCNN
    mtcnn = MTCNN(
        image_size=160,
        margin=0,
        min_face_size=20,
        thresholds=[0.6, 0.7, 0.7],
        factor=0.709,
        post_process=True,
        device=dm.device,   # ← Gán thẳng lên GPU
        keep_all=False,
    )
    logger.info(f"[Models] MTCNN loaded → device={dm.device}")

    # 3. ArcFace / FaceNet — Trích xuất embedding (ONNX)
    import onnxruntime as ort
    arcface_path = os.path.join(
        os.path.expanduser("~"),
        ".insightface", "models", "buffalo_l", "w600k_r50.onnx"
    )
    if not os.path.exists(arcface_path):
        raise FileNotFoundError(
            f"[Models] Không tìm thấy ArcFace ONNX model tại: {arcface_path}\n"
            "Chạy: python -c \"import insightface; insightface.app.FaceAnalysis(name='buffalo_l').prepare(ctx_id=0)\""
        )
    arcface_sess = ort.InferenceSession(
        arcface_path,
        providers=dm.ort_providers  # ← ["CUDAExecutionProvider", "CPUExecutionProvider"]
    )
    arcface_input_name = arcface_sess.get_inputs()[0].name

    # Log providers đang thực sự chạy
    active_providers = arcface_sess.get_providers()
    logger.info(f"[Models] ArcFace ONNX loaded → providers={active_providers}")

    return {
        "yolo":               yolo,
        "yolo_device":        yolo_device,
        "mtcnn":              mtcnn,
        "arcface":            arcface_sess,
        "arcface_input_name": arcface_input_name,
    }


# ══════════════════════════════════════════════════════════════════
# DETECT + CROP NGƯỜI BẰNG YOLO (GPU)
# ══════════════════════════════════════════════════════════════════
def detect_persons(frame: np.ndarray, models: dict, conf: float = 0.5) -> list[dict]:
    """Phát hiện người trong frame bằng YOLOv8 trên GPU."""
    if not isinstance(frame, np.ndarray):
        raise ValueError("Input phải là numpy array từ camera, không phải ảnh tĩnh.")

    results = models["yolo"].predict(
        source=frame,
        conf=conf,
        verbose=False,
        device=models["yolo_device"]
    )
    persons = []
    for result in results:
        for box in result.boxes:
            if int(box.cls[0]) != 0:  # Chỉ lấy class person (0)
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            persons.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})
    return persons


def crop_person(image: np.ndarray, person: dict, margin: float = 0.10) -> np.ndarray:
    """Cắt ROI của người với margin để không mất mặt."""
    h, w = image.shape[:2]
    x1, y1, x2, y2 = person["x1"], person["y1"], person["x2"], person["y2"]
    bw, bh = x2 - x1, y2 - y1
    x1 = max(0, int(x1 - bw * margin))
    y1 = max(0, int(y1 - bh * margin))
    x2 = min(w, int(x2 + bw * margin))
    y2 = min(h, int(y2 + bh * margin))
    return image[y1:y2, x1:x2]


# ══════════════════════════════════════════════════════════════════
# ALIGN FACE BẰNG MTCNN (GPU)
# ══════════════════════════════════════════════════════════════════
def align_face(roi: np.ndarray, mtcnn) -> Optional[torch.Tensor]:
    """Căn chỉnh khuôn mặt bằng MTCNN trên GPU. Trả về tensor [3,160,160]."""
    if roi is None or roi.size == 0:
        return None
    try:
        rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        face_tensor = mtcnn(rgb)
        return face_tensor
    except Exception as e:
        logger.debug(f"[MTCNN] Lỗi căn chỉnh: {e}")
        return None


# ══════════════════════════════════════════════════════════════════
# TRÍCH XUẤT EMBEDDING BẰNG ARCFACE (ONNX + CUDA)
# ══════════════════════════════════════════════════════════════════
def get_embedding(face_tensor: torch.Tensor, models: dict) -> Optional[np.ndarray]:
    """
    Trích xuất ArcFace embedding 512D từ face_tensor.
    ONNX Runtime tự dùng CUDAExecutionProvider nếu có GPU.
    """
    if face_tensor is None:
        return None
    try:
        # Tensor [3,160,160] → numpy HWC uint8
        img = face_tensor.permute(1, 2, 0).cpu().numpy()
        img = (img * 128.0 + 127.5).clip(0, 255).astype(np.uint8)
        img = cv2.resize(img, (112, 112))
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        img = (img.astype(np.float32) - 127.5) / 128.0
        inp = np.expand_dims(img.transpose(2, 0, 1), axis=0)

        output = models["arcface"].run(None, {models["arcface_input_name"]: inp})
        emb = output[0].flatten()

        # Chuẩn hóa L2
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        return emb
    except Exception as e:
        logger.error(f"[ArcFace] Lỗi trích xuất embedding: {e}")
        return None


# ══════════════════════════════════════════════════════════════════
# COSINE SIMILARITY (NumPy — chạy trên CPU, nhanh với vector nhỏ 512D)
# ══════════════════════════════════════════════════════════════════
def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """Tính Cosine Similarity giữa 2 vector đã chuẩn hóa L2."""
    emb1 = emb1.flatten()
    emb2 = emb2.flatten()
    norm1, norm2 = np.linalg.norm(emb1), np.linalg.norm(emb2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(emb1, emb2) / (norm1 * norm2))


def find_best_match(
    query_emb: np.ndarray,
    registered: dict,
) -> tuple[Optional[str], Optional[dict], float]:
    """
    So sánh query_emb với toàn bộ registered embeddings.
    Trả về (student_id, info_dict, best_similarity).
    """
    best_id, best_info, best_sim = None, None, -1.0
    for sid, info in registered.items():
        sim = cosine_similarity(query_emb, info["embedding"])
        if sim > best_sim:
            best_sim, best_id, best_info = sim, sid, info

    if best_sim >= SIMILARITY_THRESHOLD:
        return best_id, best_info, best_sim
    return None, None, best_sim


# ══════════════════════════════════════════════════════════════════
# LIVENESS CHECK — Chống ảnh tĩnh / ảnh in trên giấy
# ══════════════════════════════════════════════════════════════════
def liveness_check(
    cap: cv2.VideoCapture,
    first_frame: np.ndarray,
    models: dict,
    persons: list,
) -> tuple[bool, float]:
    """
    Chụp chuỗi LIVENESS_FRAME_COUNT frames, so sánh MAD.
    Nếu MAD < LIVENESS_MAD_THRESHOLD → ảnh tĩnh giả mạo.
    Trả về (is_real, mean_mad).
    """
    frames_seq = [first_frame.copy()]
    for _ in range(LIVENESS_FRAME_COUNT - 1):
        time.sleep(LIVENESS_FRAME_DELAY)
        ret, f = cap.read()
        frames_seq.append(f.copy() if ret else first_frame.copy())

    aligned_faces = []
    for f in frames_seq:
        plist = detect_persons(f, models)
        if not plist:
            continue
        roi = crop_person(f, plist[0])
        face_tensor = align_face(roi, models["mtcnn"])
        if face_tensor is None:
            continue
        # Tensor → grayscale numpy để so sánh pixel
        face_np = face_tensor.permute(1, 2, 0).cpu().numpy()
        face_np = ((face_np * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
        face_gray = cv2.cvtColor(face_np, cv2.COLOR_RGB2GRAY)
        aligned_faces.append(face_gray)

    if len(aligned_faces) < LIVENESS_FRAME_COUNT:
        logger.debug("[Liveness] Không đủ frame để kiểm tra.")
        return False, 0.0

    diffs = [
        np.mean(cv2.absdiff(aligned_faces[i], aligned_faces[i + 1]))
        for i in range(len(aligned_faces) - 1)
    ]
    mean_mad = float(np.mean(diffs))
    is_real = mean_mad >= LIVENESS_MAD_THRESHOLD
    return is_real, mean_mad


# ══════════════════════════════════════════════════════════════════
# RETRY QUEUE — Gửi lại khi server tạm mất kết nối
# ══════════════════════════════════════════════════════════════════
class RetryQueue:
    """
    Queue lưu các attendance payload chưa gửi được về server.
    Một thread nền tự động retry mỗi 10 giây.
    """
    def __init__(self, client: "JetsonClient", maxsize: int = RETRY_QUEUE_MAX):
        self._q: queue.Queue = queue.Queue(maxsize=maxsize)
        self._client = client
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def enqueue(self, payload: dict):
        try:
            self._q.put_nowait(payload)
            logger.warning(f"[RetryQueue] Thêm payload vào retry queue ({self._q.qsize()} chờ).")
        except queue.Full:
            logger.error("[RetryQueue] Queue đầy! Bỏ payload.")

    def _worker(self):
        while True:
            payload = self._q.get()
            while True:
                ok = self._client.send_attendance(payload)
                if ok:
                    logger.info(f"[RetryQueue] Retry thành công: {payload.get('student_id')}")
                    break
                logger.warning("[RetryQueue] Retry thất bại. Thử lại sau 10s...")
                time.sleep(10)
            self._q.task_done()


# ══════════════════════════════════════════════════════════════════
# MAIN PIPELINE — Vòng lặp nhận diện chính
# ══════════════════════════════════════════════════════════════════
def run_pipeline(session_id: str):
    """
    Entry point chính của Jetson Edge Pipeline.
    1. Kiểm tra & báo cáo GPU
    2. Tải model AI lên GPU
    3. Pull embeddings từ server
    4. Vòng lặp camera: detect → liveness → embed → match → send
    """

    # ── BƯỚC 0: Kiểm tra và báo cáo GPU ──────────────────────────
    dm = DeviceManager()
    print_gpu_report(dm.stats)

    if not dm.stats.available:
        logger.warning("⚠️  Không có GPU! Pipeline sẽ chạy chậm trên CPU.")
    else:
        logger.info(f"✅ Sử dụng GPU: {dm.stats.device_name} | "
                    f"VRAM: {dm.stats.total_vram_mb:.0f} MB")

    # ── BƯỚC 1: Tải model AI ─────────────────────────────────────
    logger.info("[Pipeline] Đang tải AI models...")
    try:
        models = load_ai_models(dm)
    except Exception as e:
        logger.critical(f"[Pipeline] Không tải được model: {e}")
        sys.exit(1)

    # Cập nhật GPU stats sau khi tải model
    dm.refresh(force=True)
    logger.info(
        f"[Pipeline] Model đã tải. VRAM đã dùng: "
        f"{dm.stats.used_vram_mb:.0f} MB / {dm.stats.total_vram_mb:.0f} MB"
    )

    # ── BƯỚC 2: Khởi tạo HTTP client và retry queue ──────────────
    client = JetsonClient()
    retry_queue = RetryQueue(client)

    # ── BƯỚC 3: Pull embeddings từ server ────────────────────────
    logger.info(f"[Pipeline] Pull embeddings cho session: {session_id}")
    try:
        registered = client.load_embeddings(session_id)
    except Exception as e:
        logger.critical(f"[Pipeline] Không lấy được embeddings: {e}")
        sys.exit(1)

    if not registered:
        logger.critical("[Pipeline] Embeddings rỗng! Kiểm tra session_id và server.")
        sys.exit(1)

    logger.info(f"[Pipeline] Đã load {len(registered)} embeddings.")

    # ── BƯỚC 4: Mở camera ────────────────────────────────────────
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        logger.critical(f"[Pipeline] Không mở được camera (index={CAMERA_INDEX}).")
        sys.exit(1)

    # Cài đặt camera resolution nếu cần
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    attended: set[str] = set()
    last_snapshot_time  = 0.0
    last_gpu_log_time   = 0.0
    prev_frame: Optional[np.ndarray] = None
    frame_count = 0

    banner = "═" * 58
    logger.info(f"\n{banner}")
    logger.info("  🎓  JETSON EDGE PIPELINE ĐÃ SẴN SÀNG")
    logger.info(f"  Session   : {session_id}")
    logger.info(f"  Mẫu đối sánh: {len(registered)} người")
    logger.info(f"  Ngưỡng   : {SIMILARITY_THRESHOLD}")
    logger.info(f"  Thiết bị  : {dm.stats.device_name}")
    logger.info(f"{banner}")

    # ── BƯỚC 5: Vòng lặp chính ───────────────────────────────────
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.error("[Pipeline] Mất kết nối camera!")
                break

            now = time.time()
            frame_count += 1

            # Kiểm tra camera đóng băng (frame trùng nhau)
            if prev_frame is not None:
                diff_mean = np.mean(cv2.absdiff(frame, prev_frame))
                if diff_mean == 0.0:
                    logger.warning("[Pipeline] Camera bị đóng băng hoặc ảnh tĩnh!")
                    prev_frame = frame.copy()
                    continue
            prev_frame = frame.copy()

            # Log GPU stats định kỳ
            if now - last_gpu_log_time >= GPU_LOG_INTERVAL:
                last_gpu_log_time = now
                dm.log_stats()
                dm.warn_if_hot(GPU_WARN_TEMP_C)

            # Detect người bằng YOLO trên GPU
            persons = detect_persons(frame, models)
            if not persons:
                continue

            # Snapshot cooldown
            if now - last_snapshot_time < SNAPSHOT_COOLDOWN:
                continue
            last_snapshot_time = now

            ts = datetime.now().strftime("%H:%M:%S")
            logger.info(f"[{ts}] Phát hiện {len(persons)} người → Kiểm tra liveness...")

            # Liveness check
            is_real, mean_mad = liveness_check(cap, frame, models, persons)
            if not is_real:
                logger.warning(
                    f"[{ts}] ❌ PHÁT HIỆN ẢNH TĨNH GIẢ MẠO! "
                    f"MAD={mean_mad:.4f} < {LIVENESS_MAD_THRESHOLD}"
                )
                continue

            logger.info(f"[{ts}] ✓ Liveness OK (MAD={mean_mad:.4f}) → Trích xuất embedding...")

            # Trích xuất embedding
            roi = crop_person(frame, persons[0])
            face_tensor = align_face(roi, models["mtcnn"])
            if face_tensor is None:
                logger.debug(f"[{ts}] Không tìm thấy khuôn mặt.")
                continue

            embedding = get_embedding(face_tensor, models)
            del face_tensor  # Giải phóng GPU tensor ngay sau khi dùng
            if embedding is None:
                continue

            # Tìm người khớp nhất
            matched_id, matched_info, similarity = find_best_match(embedding, registered)
            del embedding

            if matched_id is None:
                logger.info(f"[{ts}] UNKNOWN (best_sim={similarity:.4f})")
                continue

            name = matched_info["full_name"]
            code = matched_info["student_code"]

            if matched_id in attended:
                logger.info(f"[{ts}] {name} ({code}) — Đã điểm danh rồi.")
                continue

            # Điểm danh thành công → Gửi về server
            logger.info(f"[{ts}] ✅ PRESENT: {name} | {code} | sim={similarity:.4f}")
            payload = {
                "session_id":  session_id,
                "student_id":  matched_id,
                "confidence":  round(float(similarity), 6),
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "source":      "jetson_edge",
                "device_info": {
                    "gpu":  dm.stats.device_name,
                    "temp": dm.stats.gpu_temp_c,
                    "vram": f"{dm.stats.used_vram_mb:.0f}/{dm.stats.total_vram_mb:.0f} MB",
                }
            }

            ok = client.send_attendance(payload)
            if ok:
                attended.add(matched_id)
                logger.info(f"       → Đã ghi điểm danh (total: {len(attended)}/{len(registered)})")
            else:
                logger.warning(f"       → Server không phản hồi! Đưa vào retry queue.")
                retry_queue.enqueue(payload)
                attended.add(matched_id)  # Vẫn đánh dấu để tránh nhận diện lại

    except KeyboardInterrupt:
        logger.info("\n[Pipeline] Người dùng yêu cầu thoát (Ctrl+C).")
    finally:
        cap.release()
        logger.info("[Pipeline] Đã đóng camera và giải phóng tài nguyên.")

        # In thống kê cuối phiên
        final_stats = dm.refresh(force=True)
        logger.info(
            f"[Pipeline] Kết thúc phiên: "
            f"{len(attended)}/{len(registered)} sinh viên điểm danh. "
            f"GPU: {final_stats.gpu_temp_c:.1f}°C | "
            f"VRAM còn lại: {final_stats.free_vram_mb:.0f} MB"
        )
