import os
import sys
import cv2
import time
import uuid
import argparse
import pickle
import numpy as np
import torch
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# Dlib tự phát hiện khuôn mặt — KHÔNG cần YOLO + MTCNN
from app.shared.similarity_service import cosine_similarity
from app.services_dlib.dlib_service import dlib_service

# ══════════════════════════════════════════════════════════════════
# CẤU HÌNH (đọc từ .env)
# ══════════════════════════════════════════════════════════════════
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME",     "attendance_db"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# Dlib face_recognition trả về vector 128D — ngưỡng khác với 512D
SIMILARITY_THRESHOLD = float(os.getenv("DLIB_THRESHOLD",   "0.65"))
SNAPSHOT_COOLDOWN    = float(os.getenv("SNAPSHOT_COOLDOWN", "3.0"))
CAMERA_INDEX         = int(os.getenv("CAMERA_INDEX",        "0"))
MODEL_NAME           = "dlib"

# Thiết bị chạy (Bắt buộc phải có GPU CUDA)
if not torch.cuda.is_available():
    print("[!] LỖI: Không phát hiện thấy GPU CUDA! Hệ thống bắt buộc phải sử dụng GPU để chạy.")
    sys.exit(1)

print("[Dlib Pipeline] Khởi động...")
print("[Dlib] Lưu ý: Dlib tự phát hiện khuôn mặt, không cần YOLO + MTCNN.")

# ══════════════════════════════════════════════════════════════════
# CHUYỂN ĐỔI EMBEDDING ↔ BYTES
# ══════════════════════════════════════════════════════════════════
def bytes_to_embedding(raw: bytes) -> np.ndarray:
    return np.frombuffer(raw, dtype=np.float32).copy()

# ══════════════════════════════════════════════════════════════════
# TRUY VẤN POSTGRESQL
# ══════════════════════════════════════════════════════════════════
def load_registered_embeddings_db(conn) -> dict:
    """Tải Dlib embeddings (128D) hợp lệ từ PostgreSQL."""
    sql = """
        SELECT
            s.id            AS student_id,
            s.full_name,
            s.student_code,
            s.research_id,
            fe.embedding    AS emb_bytes
        FROM public.face_embeddings fe
        JOIN public.students s ON fe.student_id = s.id
        WHERE fe.model_name = 'dlib'
          AND fe.is_valid   = true
          AND s.is_active   = true
        ORDER BY s.full_name
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()

    registered = {}
    for row in rows:
        sid = str(row["student_id"])
        emb = bytes_to_embedding(bytes(row["emb_bytes"]))
        registered[sid] = {
            "full_name":    row["full_name"]    or "Chưa có tên",
            "student_code": row["student_code"] or "",
            "research_id":  row["research_id"]  or "",
            "embedding":    emb,
        }
    print(f"[DB] Đã tải {len(registered)} sinh viên có Dlib embedding.")
    return registered

def get_session_info(conn, session_id: str) -> dict:
    sql = """
        SELECT cs.id AS session_id, cs.started_at, c.class_code, c.subject_name
        FROM public.class_sessions cs
        JOIN public.classes c ON cs.class_id = c.id
        WHERE cs.id = %s::uuid AND cs.ended_at IS NULL
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(sql, (session_id,))
    row = cur.fetchone()
    cur.close()
    if row is None:
        raise ValueError(f"Không tìm thấy phiên điểm danh đang mở: {session_id}")
    return dict(row)

def get_enrolled_students(conn, session_id: str) -> set:
    sql = """
        SELECT ce.student_id::text
        FROM public.class_enrollments ce
        JOIN public.class_sessions cs ON cs.class_id = ce.class_id
        WHERE cs.id = %s::uuid
    """
    cur = conn.cursor()
    cur.execute(sql, (session_id,))
    rows = cur.fetchall()
    cur.close()
    return {r[0] for r in rows}

def record_attendance_db(conn, session_id: str, student_id: str, confidence: float):
    sql = """
        INSERT INTO public.attendance_records
            (session_id, student_id, status, confidence, detected_at)
        VALUES (%s::uuid, %s::uuid, 'PRESENT'::public.attendance_status, %s, %s)
        ON CONFLICT (session_id, student_id) DO NOTHING
    """
    cur = conn.cursor()
    cur.execute(sql, (session_id, student_id, round(float(confidence), 6), datetime.now(timezone.utc)))
    conn.commit()
    cur.close()

# ══════════════════════════════════════════════════════════════════
# CHẾ ĐỘ CỤC BỘ
# ══════════════════════════════════════════════════════════════════
def load_local_dataset(dataset_dir: str) -> dict:
    """
    Quét thư mục dataset để trích xuất Dlib embeddings.
    Dlib tự phát hiện mặt từ ảnh trực tiếp — không cần YOLO/MTCNN.
    """
    print(f"\n[Local Mode] Đang quét: {dataset_dir}")
    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir, exist_ok=True)
        return {}

    cache_path = os.path.join(dataset_dir, "dlib_local_cache.pkl")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"[Cache] Lỗi: {e}. Trích xuất lại...")

    registered = {}
    for subdir in os.listdir(dataset_dir):
        folder = os.path.join(dataset_dir, subdir)
        if not os.path.isdir(folder): continue
        images = [f for f in os.listdir(folder) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        embs = []
        for img_name in images:
            img = cv2.imread(os.path.join(folder, img_name))
            if img is None: continue
            try:
                # Dlib xử lý toàn bộ ảnh, tự tìm mặt bên trong
                emb = dlib_service.get_embedding(img)
                if emb is not None:
                    embs.append(np.array(emb, dtype=np.float32))
            except Exception as e:
                print(f"  Lỗi {img_name}: {e}")

        if embs:
            mean_emb = np.mean(embs, axis=0)
            mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-8)
            sid = str(uuid.uuid4())
            registered[sid] = {
                "full_name":    subdir.replace("_", " "),
                "student_code": subdir,
                "research_id":  "",
                "embedding":    mean_emb,
            }
            print(f"  ✓ {subdir} ({len(embs)} ảnh, vector 128D)")

    if registered:
        with open(cache_path, "wb") as f:
            pickle.dump(registered, f)

    return registered

# ══════════════════════════════════════════════════════════════════
# TÌM KHỚP TỐT NHẤT
# ══════════════════════════════════════════════════════════════════
def find_best_match(query_emb: np.ndarray, registered: dict, enrolled_ids: set = None):
    best_id, best_info, best_sim = None, None, -1.0
    for sid, info in registered.items():
        if enrolled_ids is not None and sid not in enrolled_ids: continue
        sim = cosine_similarity(query_emb, info["embedding"])
        if sim > best_sim:
            best_sim, best_id, best_info = sim, sid, info
    if best_sim >= SIMILARITY_THRESHOLD:
        return best_id, best_info, best_sim
    return None, None, best_sim

# ══════════════════════════════════════════════════════════════════
# PIPELINE CHÍNH
# ══════════════════════════════════════════════════════════════════
def run_pipeline(session_id: str = None, is_local: bool = False, dataset_dir: str = "dataset"):
    conn = None
    registered = {}
    enrolled_ids = None
    session_info = {"class_code": "LOCAL", "subject_name": "Dlib Cục Bộ"}

    # 1. Kết nối DB hoặc load local
    if is_local or session_id is None:
        print("[Dlib] Chế độ CỤC BỘ.")
        registered = load_local_dataset(dataset_dir)
    else:
        print("[Dlib] Chế độ POSTGRESQL.")
        try:
            conn         = psycopg2.connect(**DB_CONFIG)
            session_info = get_session_info(conn, session_id)
            enrolled_ids = get_enrolled_students(conn, session_id)
            registered   = load_registered_embeddings_db(conn)
            print(f"[Session] {session_info['class_code']} — {session_info['subject_name']} | {len(enrolled_ids)} SV")
        except Exception as e:
            print(f"[Lỗi DB] {e} → Chuyển về Local Mode.")
            is_local   = True
            registered = load_local_dataset(dataset_dir)

    eligible = registered
    if not is_local and enrolled_ids:
        eligible = {k: v for k, v in registered.items() if k in enrolled_ids}

    if not eligible:
        print("[!] Không có dữ liệu embedding. Thoát.")
        if conn: conn.close()
        return

    # 2. Mở camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[!] Không mở được camera (index={CAMERA_INDEX}).")
        if conn: conn.close()
        return

    attended   = set()
    last_snap  = 0.0
    prev_frame = None

    # ── Liveness check cho Dlib ──────────────────────────────────
    # Dlib không dùng MTCNN nên liveness check dựa vào frame grayscale toàn cảnh
    LIVENESS_THRESHOLD  = 1.4
    LIVENESS_REGION_PCT = 0.25  # Chỉ lấy vùng trung tâm 25% để so sánh

    print("\n" + "═"*60)
    print("  🎓  DLIB PIPELINE — ĐIỂM DANH REALTIME")
    print(f"  Lớp  : {session_info['class_code']} — {session_info['subject_name']}")
    print(f"  Model: Dlib face_recognition (128D) | Ngưỡng: {SIMILARITY_THRESHOLD}")
    print(f"  Mẫu  : {len(eligible)} người   |  Nhấn Q để thoát")
    print("  Lưu ý: Dlib tự phát hiện mặt — không dùng YOLO/MTCNN")
    print("═"*60 + "\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[!] Mất tín hiệu camera.")
            break

        now     = time.time()
        display = frame.copy()

        # Kiểm tra camera đóng băng
        if prev_frame is not None and np.mean(cv2.absdiff(frame, prev_frame)) == 0.0:
            cv2.putText(display, "LỖI: CAMERA ĐÓNG BĂNG!", (15, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.imshow("Dlib - Diem Danh Tu Dong", display)
            prev_frame = frame.copy()
            if cv2.waitKey(1) & 0xFF == ord("q"): break
            continue
        prev_frame = frame.copy()

        if now - last_snap >= SNAPSHOT_COOLDOWN:
            last_snap = now
            ts = datetime.now().strftime("%H:%M:%S")

            snapshot = frame.copy()

            # Thử trích xuất embedding từ snapshot
            query_emb_raw = dlib_service.get_embedding(snapshot)
            del snapshot

            if query_emb_raw is None:
                # Không phát hiện mặt trong frame này
                cv2.putText(display, "Không tìm thấy khuôn mặt", (15, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 255), 2)
            else:
                print(f"\n[{ts}] Phát hiện khuôn mặt → Kiểm tra liveness...")

                # Liveness check: so sánh vùng trung tâm 3 frame
                frames_seq = [frame.copy()]
                for _ in range(2):
                    time.sleep(0.12)
                    ok, f = cap.read()
                    frames_seq.append(f.copy() if ok else frame.copy())

                h, w = frame.shape[:2]
                cy1 = int(h * (0.5 - LIVENESS_REGION_PCT))
                cy2 = int(h * (0.5 + LIVENESS_REGION_PCT))
                cx1 = int(w * (0.5 - LIVENESS_REGION_PCT))
                cx2 = int(w * (0.5 + LIVENESS_REGION_PCT))

                grays = [
                    cv2.cvtColor(f[cy1:cy2, cx1:cx2], cv2.COLOR_BGR2GRAY)
                    for f in frames_seq
                ]
                d1 = np.mean(cv2.absdiff(grays[0], grays[1]))
                d2 = np.mean(cv2.absdiff(grays[1], grays[2]))
                mean_mad = (d1 + d2) / 2.0

                if mean_mad < LIVENESS_THRESHOLD:
                    print(f"[{ts}] ❌ ẢNH TĨNH GIẢ MẠO! MAD={mean_mad:.4f}")
                    cv2.putText(display, "GIA MAO ANH TINH!", (15, 80),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                else:
                    print(f"[{ts}] ✓ Liveness OK (MAD={mean_mad:.4f}) → Đối sánh...")
                    query_emb = np.array(query_emb_raw, dtype=np.float32)
                    matched_id, matched_info, similarity = find_best_match(query_emb, eligible, enrolled_ids)
                    del query_emb

                    if matched_id is None:
                        label = f"UNKNOWN (sim={similarity:.3f})"
                        color = (0, 0, 255)
                        print(f"[{ts}] UNKNOWN — best_sim={similarity:.4f}")
                    elif matched_id in attended:
                        name  = matched_info["full_name"]
                        code  = matched_info["student_code"]
                        label = f"{name} ({code}) — Đã điểm danh"
                        color = (0, 165, 255)
                        print(f"[{ts}] {name} đã điểm danh rồi.")
                    else:
                        name  = matched_info["full_name"]
                        code  = matched_info["student_code"]
                        label = f"{name} ({code}) {similarity:.3f}"
                        color = (0, 255, 0)
                        print(f"[{ts}] ✅ PRESENT: {name} | {code} | sim={similarity:.4f}")
                        if not is_local and conn:
                            try:
                                record_attendance_db(conn, session_id, matched_id, similarity)
                                print("       → Đã lưu DB.")
                            except Exception as e:
                                print(f"       [DB Error] {e}")
                        attended.add(matched_id)

                    cv2.putText(display, label, (15, 80),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        cv2.putText(display, f"Diem danh: {len(attended)}/{len(eligible)}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(display, f"{session_info['class_code']} | Dlib 128D | Q=Thoat",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        cv2.imshow("Dlib - Diem Danh Tu Dong", display)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("\n[Hệ thống] Người dùng thoát.")
            break

    cap.release()
    cv2.destroyAllWindows()
    attended.clear()
    registered.clear()
    if conn: conn.close()
    print("\n[Dlib] Đã kết thúc phiên và giải phóng tài nguyên.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hệ thống điểm danh Dlib face_recognition")
    parser.add_argument("session_id", nargs="?", default=None, help="UUID phiên học (PostgreSQL)")
    parser.add_argument("--local",     action="store_true",  help="Chạy cục bộ không cần DB")
    parser.add_argument("--dataset",   default="dataset",    help="Thư mục ảnh dataset cục bộ")
    parser.add_argument("--threshold", type=float, default=None,
                        help="Ngưỡng cosine similarity (0.0-1.0). Mặc định: DLIB_THRESHOLD trong .env hoặc 0.65")
    args = parser.parse_args()

    if args.threshold is not None:
        if not 0.0 < args.threshold < 1.0:
            print("[Lỗi] --threshold phải nằm trong khoảng (0.0, 1.0)")
            sys.exit(1)
        SIMILARITY_THRESHOLD = args.threshold
        print(f"[Config] Ngưỡng nhận diện được đặt thủ công: {SIMILARITY_THRESHOLD}")

    if args.local or args.session_id is None:
        run_pipeline(is_local=True, dataset_dir=args.dataset)
    else:
        try:
            uuid.UUID(args.session_id.strip())
            run_pipeline(session_id=args.session_id.strip(), dataset_dir=args.dataset)
        except ValueError:
            print(f"[Lỗi] session_id không hợp lệ: '{args.session_id}'")
            sys.exit(1)
