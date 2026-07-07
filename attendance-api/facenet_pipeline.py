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
from collections import deque  # Thêm hàng đợi để tối ưu buffer camera

load_dotenv()

# Import shared services
from app.shared.yolo_detector       import detect_person, crop_person
from app.shared.mtcnn_alignment     import align_face
from app.shared.similarity_service  import cosine_similarity
from app.service_facenet.facenet_service import get_embedding

# ══════════════════════════════════════════════════════════════════
# CẤU HÌNH HỆ THỐNG
# ══════════════════════════════════════════════════════════════════
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME",     "attendance_db"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),   # Đặt trong file .env
}

SIMILARITY_THRESHOLD = float(os.getenv("FACENET_THRESHOLD",  "0.65"))
SNAPSHOT_COOLDOWN    = float(os.getenv("SNAPSHOT_COOLDOWN",  "3.0"))
_cam_index_raw       = os.getenv("CAMERA_INDEX",         "0")
CAMERA_INDEX         = int(_cam_index_raw) if _cam_index_raw.isdigit() else _cam_index_raw

# Cấu hình loại camera sử dụng trên Jetson (CSI hoặc USB)
USE_CSI = os.getenv("USE_CSI", "true").lower() == "true"

# Thiết bị chạy (Bắt buộc phải có GPU CUDA)
if not torch.cuda.is_available():
    print("[!] LỖI: Không phát hiện thấy GPU CUDA! Hệ thống bắt buộc phải sử dụng GPU để chạy.")
    sys.exit(1)

DEVICE = "cuda"
print(f"[FaceNet Pipeline] Thiết bị chạy: {DEVICE}")

# ══════════════════════════════════════════════════════════════════
# HÀM TẠO GSTREAMER PIPELINE CHO CAMERA CSI JETSON
# ══════════════════════════════════════════════════════════════════
def get_gstreamer_pipeline(sensor_id=0, width=1280, height=720, flip_method=2):
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM),width={width},height={height},format=NV12,framerate=30/1 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw,format=BGRx ! "
        f"videoconvert ! "
        f"video/x-raw,format=BGR ! "
        f"appsink drop=true max-buffers=1 sync=false"
    )

# ══════════════════════════════════════════════════════════════════
# CHUYỂN ĐỔI EMBEDDING ↔ BYTES
# ══════════════════════════════════════════════════════════════════
def bytes_to_embedding(raw: bytes) -> np.ndarray:
    """Chuyển đổi dữ liệu bytea từ PostgreSQL -> numpy array float32 (512,)."""
    return np.frombuffer(raw, dtype=np.float32).copy()

def embedding_to_bytes(emb: np.ndarray) -> bytes:
    """Chuyển đổi numpy array float32 -> bytes để INSERT vào PostgreSQL."""
    return emb.astype(np.float32).tobytes()

# ══════════════════════════════════════════════════════════════════
# TRUY VẤN POSTGRESQL DATABASE
# ══════════════════════════════════════════════════════════════════
def load_registered_embeddings_db(conn) -> dict:
    """Tải tất cả FaceNet embeddings hợp lệ từ PostgreSQL."""
    sql = """
        SELECT
            s.id            AS student_id,
            s.full_name,
            s.student_code,
            s.research_id,
            fe.embedding    AS emb_bytes
        FROM public.face_embeddings fe
        JOIN public.students s ON fe.student_id = s.id
        WHERE fe.model_name = 'facenet'
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
            "full_name":    row["full_name"] or "Chưa có tên",
            "student_code": row["student_code"] or "",
            "research_id":  row["research_id"] or "",
            "embedding":    emb,
        }

    print(f"[Database] Đã tải {len(registered)} sinh viên có embedding FaceNet từ PostgreSQL.")
    return registered

def get_session_info(conn, session_id: str) -> dict:
    """Lấy thông tin phiên học từ class_sessions."""
    sql = """
        SELECT
            cs.id           AS session_id,
            cs.started_at,
            c.class_code,
            c.subject_name
        FROM public.class_sessions cs
        JOIN public.classes c ON cs.class_id = c.id
        WHERE cs.id = %s::uuid
          AND cs.ended_at IS NULL
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(sql, (session_id,))
    row = cur.fetchone()
    cur.close()

    if row is None:
        raise ValueError(f"Không tìm thấy phiên điểm danh đang mở với ID: {session_id}")
    return dict(row)

def get_enrolled_students(conn, session_id: str) -> set:
    """Lấy danh sách sinh viên đăng ký lớp học này."""
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
    return {row[0] for row in rows}

def record_attendance_db(conn, session_id: str, student_id: str, confidence: float):
    """Ghi dữ liệu điểm danh vào PostgreSQL."""
    sql = """
        INSERT INTO public.attendance_records
            (session_id, student_id, status, confidence, detected_at)
        VALUES
            (%s::uuid, %s::uuid, 'PRESENT'::public.attendance_status, %s, %s)
        ON CONFLICT (session_id, student_id) DO NOTHING
    """
    cur = conn.cursor()
    cur.execute(sql, (
        session_id,
        student_id,
        round(float(confidence), 6),
        datetime.now(timezone.utc),
    ))
    conn.commit()
    cur.close()

# ══════════════════════════════════════════════════════════════════
# XỬ LÝ CHẾ ĐỘ THƯ MỤC CỤC BỘ (LOCAL MODE FALLBACK)
# ══════════════════════════════════════════════════════════════════
def load_local_dataset(dataset_dir: str) -> dict:
    """Quét thư mục dataset_dir, lưu TẤT CẢ embedding riêng lẻ của từng ảnh."""
    print(f"\n[Local Mode] Đang quét thư mục dataset: {dataset_dir}")
    if not os.path.exists(dataset_dir):
        print(f"[Cảnh báo] Thư mục '{dataset_dir}' không tồn tại. Tạo mới thư mục trống.")
        os.makedirs(dataset_dir, exist_ok=True)
        return {}

    cache_path = os.path.join(dataset_dir, "facenet_local_cache.pkl")
    subdirs = [d for d in os.listdir(dataset_dir) if os.path.isdir(os.path.join(dataset_dir, d)) and d != "__pycache__"]

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                cached_data = pickle.load(f)
            
            cached_folders = {info["student_code"]: info for info in cached_data.values()}
            if set(subdirs) == set(cached_folders.keys()):
                cache_valid = True
                for subdir in subdirs:
                    folder = os.path.join(dataset_dir, subdir)
                    images = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                    cached_info = cached_folders.get(subdir)
                    if not cached_info or set(images) != set(cached_info.get("images", [])):
                        cache_valid = False
                        break
                
                if cache_valid:
                    print(f"[Local Mode] Đã tải cache embeddings hợp lệ từ: {cache_path}")
                    return cached_data
                else:
                    print(f"[Local Mode] Phát hiện thay đổi trong ảnh/thư mục dataset. Đang tự động quét lại...")
            else:
                print(f"[Local Mode] Phát hiện thêm/bớt thư mục người học. Đang tự động quét lại...")
        except Exception as e:
            print(f"[Cảnh báo] Lỗi khi load cache: {e}. Tiến hành quét lại.")

    registered = {}
    for subdir in subdirs:
        student_name   = subdir
        student_folder = os.path.join(dataset_dir, subdir)
        images = [f for f in os.listdir(student_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        embeddings_list = []
        for img_name in images:
            img_path = os.path.join(student_folder, img_name)
            try:
                img = cv2.imread(img_path)
                if img is None:
                    continue
                persons = detect_person(img)
                if not persons:
                    continue
                roi         = crop_person(img, persons[0])
                face_tensor = align_face(roi)
                if face_tensor is not None:
                    emb = get_embedding(face_tensor)
                    if emb is not None:
                        arr = emb.numpy() if hasattr(emb, 'numpy') else np.array(emb, dtype=np.float32)
                        arr = arr / (np.linalg.norm(arr) + 1e-8)  # L2-normalize
                        embeddings_list.append(arr)
            except Exception as e:
                print(f"  Lỗi khi trích xuất {img_path}: {e}")

        if embeddings_list:
            sid = str(uuid.uuid4())
            registered[sid] = {
                "full_name":    student_name.replace("_", " "),
                "student_code": student_name,
                "research_id":  "",
                "embeddings":   embeddings_list,
                "images":       images,
            }
            print(f"  ✓ {student_name} ({len(embeddings_list)} ảnh)")

    if registered:
        with open(cache_path, "wb") as f:
            pickle.dump(registered, f)
        print(f"[Local Mode] Đã lưu cache tự động tại {cache_path}")

    return registered

# ══════════════════════════════════════════════════════════════════
# HÀM SO SÁNH EMBEDDING TÌM KẾT QUẢ TỐT NHẤT
# ══════════════════════════════════════════════════════════════════
def find_best_match(query_emb: np.ndarray, registered: dict, enrolled_ids: set = None):
    """Top-3 Voting kiểm tra độ tương đồng hệ màu."""
    all_scores = []
    for sid, info in registered.items():
        if enrolled_ids is not None and sid not in enrolled_ids:
            continue

        emb_list = info.get("embeddings") or [info.get("embedding")]
        for emb in emb_list:
            if emb is None:
                continue
            sim = cosine_similarity(query_emb, emb)
            all_scores.append((sim, sid, info))

    if not all_scores:
        return None, None, -1.0

    all_scores.sort(key=lambda x: x[0], reverse=True)
    top3 = all_scores[:3]
    avg_sim = sum(s[0] for s in top3) / len(top3)

    from collections import Counter
    vote_counter = Counter(s[1] for s in top3)
    winner_sid   = vote_counter.most_common(1)[0][0]
    winner_info  = registered[winner_sid]

    names = [registered[s[1]]["full_name"] for s in top3]
    sims  = [round(s[0], 4) for s in top3]
    print(f"    [Top3] {list(zip(names, sims))} | avg={avg_sim:.4f} | winner={winner_info['full_name']}")

    if avg_sim >= SIMILARITY_THRESHOLD:
        return winner_sid, winner_info, avg_sim
    return None, None, avg_sim

# ══════════════════════════════════════════════════════════════════
# XỬ LÝ FRAME CAMERA (SNAPSHOT)
# ══════════════════════════════════════════════════════════════════
def process_frame(frame: np.ndarray):
    """Xử lý 1 khung hình camera: Phát hiện người -> Trích xuất mặt -> Tính embedding"""
    image, persons = detect_person(frame)
    if not persons:
        return None, None

    for person in persons:
        roi = crop_person(image, person)
        face_tensor = align_face(roi)
        if face_tensor is not None:
            embedding = get_embedding(face_tensor)
            if embedding is not None:
                return embedding.numpy(), person
    return None, None

# ══════════════════════════════════════════════════════════════════
# HÀM CHẠY CHÍNH (MAIN PROCESS)
# ══════════════════════════════════════════════════════════════════
def run_pipeline(session_id: str = None, is_local: bool = False, dataset_dir: str = "dataset"):
    conn = None
    registered = {}
    enrolled_ids = None
    session_info = {"class_code": "LOCAL_MODE", "subject_name": "Nhận diện Cục bộ"}
    
    # 1. KẾT NỐI DATABASE HOẶC LOAD LOCAL DATASET
    if is_local or session_id is None:
        print("[FaceNet Pipeline] Chạy ở chế độ CỤC BỘ (Local Mode).")
        registered = load_local_dataset(dataset_dir)
        if not registered:
            print("[Cảnh báo] Cơ sở dữ liệu cục bộ rỗng! Hãy thêm các thư mục ảnh vào thư mục 'dataset/'.")
    else:
        print("[FaceNet Pipeline] Chạy ở chế độ POSTGRESQL DB.")
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            print("[DB] Kết nối PostgreSQL thành công.")
            
            session_info = get_session_info(conn, session_id)
            print(f"[Session] Lớp: {session_info['class_code']} - {session_info['subject_name']}")
            
            enrolled_ids = get_enrolled_students(conn, session_id)
            print(f"[Session] Sĩ số lớp: {len(enrolled_ids)} sinh viên")
            
            registered = load_registered_embeddings_db(conn)
        except Exception as e:
            print(f"[Lỗi DB] Không kết nối được cơ sở dữ liệu: {e}")
            print("[Hệ thống] Tự động chuyển về chế độ CỤC BỘ (Local Mode).")
            is_local = True
            registered = load_local_dataset(dataset_dir)

    eligible = registered
    if not is_local and enrolled_ids is not None:
        eligible = {sid: info for sid, info in registered.items() if sid in enrolled_ids}
        print(f"[Database] Số sinh viên thuộc lớp đã có FaceNet embedding: {len(eligible)} người")

    if not eligible:
        print("[!] Không tìm thấy dữ liệu khuôn mặt để đối sánh. Tiến hành tắt chương trình.")
        if conn:
            conn.close()
        return

    # 2. KHỞI CHẠY CAMERA VÀ ĐỐI SÁNH VỚI GSTREAMER HOẶC V4L2
    if USE_CSI and str(CAMERA_INDEX).isdigit():
        print(f"[Camera] Đang mở Camera CSI (Sensor ID: {CAMERA_INDEX}) qua GStreamer...")
        gstreamer_str = get_gstreamer_pipeline(sensor_id=int(CAMERA_INDEX))
        cap = cv2.VideoCapture(gstreamer_str, cv2.CAP_GSTREAMER)
    else:
        print(f"[Camera] Đang mở Webcam thông thường (Index: {CAMERA_INDEX})...")
        cap = cv2.VideoCapture(int(CAMERA_INDEX) if str(CAMERA_INDEX).isdigit() else CAMERA_INDEX)

    if not cap.isOpened():
        print(f"[!] Không mở được camera (index={CAMERA_INDEX}). Vui lòng kiểm tra lại kết nối phần cứng.")
        if conn:
            conn.close()
        return

    attended = set()  
    last_snapshot_time = 0.0
    
    # Khởi tạo bộ đệm lưu 3 khung hình liên tục (Hỗ trợ liveness check mượt mà)
    frame_buffer = deque(maxlen=3)

    print("\n" + "═"*60)
    print("  🎓  HỆ THỐNG ĐIỂM DANH FACENET REALTIME ĐÃ SẴN SÀNG")
    print(f"  Lớp/Chương trình: {session_info['class_code']} — {session_info['subject_name']}")
    print(f"  Ngưỡng nhận dạng: {SIMILARITY_THRESHOLD}")
    print(f"  Tổng số mẫu đối sánh: {len(eligible)} người")
    print("  👉 Nhấn phím 'Q' trên màn hình camera để THOÁT")
    print("═"*60 + "\n")

    prev_frame = None
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[!] Mất kết nối camera.")
            break

        now = time.time()
        display = frame.copy()
        
        # Liên tục lưu khung hình hiện tại vào bộ đệm tuần hoàn
        frame_buffer.append(frame.copy())

        # ── KIỂM TRA CAMERA ĐÓNG BĂNG ──
        if prev_frame is not None:
            diff = cv2.absdiff(frame, prev_frame)
            mean_diff = np.mean(diff)
            if mean_diff == 0.0:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] [LỖI] Phát hiện luồng camera bị đóng băng!")
                cv2.putText(display, "ERROR: STATIC INPUT FEED!", (15, 100), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow("FaceNet - Diem Danh Tu Dong", display)
                prev_frame = frame.copy()
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                continue

        prev_frame = frame.copy()

        # Real-time preview: Phát hiện người bằng YOLOv8
        persons = detect_person(frame)
        for person in persons:
            cv2.rectangle(display, 
                          (person["x1"], person["y1"]), 
                          (person["x2"], person["y2"]), 
                          (0, 255, 0), 2)

        # Xử lý snapshot sau mỗi khoảng cooldown (Không dùng time.sleep)
        if persons and (now - last_snapshot_time >= SNAPSHOT_COOLDOWN):
            # Chỉ xử lý khi bộ đệm thu thập đủ ít nhất 3 frames gần nhất
            if len(frame_buffer) < 3:
                continue

            last_snapshot_time = now
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{ts}] Kiểm tra liveness (MAD) dựa trên dữ liệu bộ đệm...")

            aligned_faces = []
            person_box = persons[0]  
            buffer_list = list(frame_buffer)
            
            for idx, f in enumerate(buffer_list):
                # Khung hình cuối cùng trong mảng chính là khung hình hiện tại (đã chạy YOLO)
                if idx == len(buffer_list) - 1:
                    persons_seq = persons
                else:
                    persons_seq = detect_person(f)
                    
                if persons_seq:
                    roi_seq = crop_person(f, persons_seq[0])
                    face_tensor_seq = align_face(roi_seq)
                    if face_tensor_seq is not None:
                        face_np = face_tensor_seq.permute(1, 2, 0).cpu().numpy()
                        face_np = ((face_np * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
                        face_gray = cv2.cvtColor(face_np, cv2.COLOR_RGB2GRAY)
                        aligned_faces.append(face_gray)

            # ── KIỂM TRA LIVENESS (CHỐNG GIẢ MẠO ẢNH TĨNH) ──
            is_spoof = False
            mean_mad = 0.0
            
            if len(aligned_faces) == 3:
                diff1 = cv2.absdiff(aligned_faces[0], aligned_faces[1])
                diff2 = cv2.absdiff(aligned_faces[1], aligned_faces[2])
                mad1 = np.mean(diff1)
                mad2 = np.mean(diff2)
                mean_mad = (mad1 + mad2) / 2.0
                
                if mean_mad < 1.4:
                    is_spoof = True
            else:
                print(f"[{ts}] Không trích xuất đủ khuôn mặt từ chuỗi khung hình (bỏ qua liveness check).")
                continue

            if is_spoof:
                print(f"[{ts}] [LỖI] PHÁT HIỆN GIẢ MẠO! Độ biến thiên MAD: {mean_mad:.4f}")
                label = "LOI: ANH TINH GIA MAO!"
                color = (0, 0, 255) 
                
                if person_box is not None:
                    cv2.rectangle(display, (person_box["x1"], person_box["y1"]), (person_box["x2"], person_box["y2"]), color, 3)
                    cv2.putText(display, label, (person_box["x1"], max(person_box["y1"] - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
                continue

            print(f"[{ts}] ✓ Liveness thông qua. Độ biến thiên MAD: {mean_mad:.4f}. Tiến hành đối sánh...")

            # ── TIẾN HÀNH ĐỐI SÁNH EMBEDDING KHI LÀ NGƯỜI THẬT ──
            last_roi = crop_person(buffer_list[-1], persons[0])
            last_face_tensor = align_face(last_roi)
            
            if last_face_tensor is None:
                print(f"[{ts}] Không tìm thấy khuôn mặt ở khung hình cuối.")
                continue
                
            embedding_tensor = get_embedding(last_face_tensor)
            if embedding_tensor is None:
                print(f"[{ts}] Không trích xuất được FaceNet embedding.")
                continue
                
            query_emb = embedding_tensor.numpy()

            matched_id, matched_info, similarity = find_best_match(query_emb, eligible, enrolled_ids)
            del query_emb  

            if matched_id is None:
                label = f"UNKNOWN (sim={similarity:.3f})"
                color = (0, 0, 255)
                print(f"[{ts}] UNKNOWN — Độ tương đồng tốt nhất: {similarity:.4f}")
            
            elif matched_id in attended:
                name = matched_info["full_name"]
                code = matched_info["student_code"]
                label = f"{name} ({code}) - Attended"
                color = (0, 165, 255)
                print(f"[{ts}] Sinh viên {name} ({code}) đã điểm danh trước đó.")
            
            else:
                name = matched_info["full_name"]
                code = matched_info["student_code"]
                label = f"{name} ({code}) {similarity:.3f}"
                color = (0, 255, 0)
                print(f"[{ts}] ✓ PRESENT: {name} | Mã số: {code} | Độ khớp: {similarity:.4f}")

                if not is_local and conn is not None:
                    try:
                        record_attendance_db(conn, session_id, matched_id, similarity)
                        print("       → Đã lưu kết quả điểm danh vào Database.")
                    except Exception as db_err:
                        print(f"       [Lỗi DB] Không ghi được điểm danh: {db_err}")

                attended.add(matched_id)

            if person_box is not None:
                cv2.rectangle(display, (person_box["x1"], person_box["y1"]), (person_box["x2"], person_box["y2"]), color, 3)
                cv2.putText(display, label, (person_box["x1"], max(person_box["y1"] - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Hiển thị HUD thông tin hệ thống
        cv2.putText(display, f"Diem danh: {len(attended)}/{len(eligible)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(display, f"{session_info['class_code']} | Q=Thoat", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        cv2.imshow("FaceNet - Diem Danh Tu Dong", display)
        
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("\n[Hệ thống] Người dùng yêu cầu thoát.")
            break

    cap.release()
    cv2.destroyAllWindows()
    attended.clear()
    registered.clear()
    frame_buffer.clear()
    if conn:
        conn.close()
    print("\n[Hệ thống] Đã kết thúc phiên nhận diện và giải phóng thiết bị.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hệ thống điểm danh khuôn mặt bằng mô hình FaceNet")
    parser.add_argument("session_id", nargs="?", default=None, help="UUID phiên học trong database (PostgreSQL)")
    parser.add_argument("--local",     action="store_true",    help="Chạy chế độ cục bộ không kết nối PostgreSQL")
    parser.add_argument("--dataset",   default="dataset",      help="Đường dẫn đến thư mục chứa ảnh đối sánh cục bộ")
    parser.add_argument("--threshold", type=float, default=None, help="Ngưỡng cosine similarity (0.0-1.0)")

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
            run_pipeline(session_id=args.session_id.strip(), is_local=False, dataset_dir=args.dataset)
        except ValueError:
            print(f"[Lỗi] session_id không đúng định dạng UUID: '{args.session_id}'")
            sys.exit(1)