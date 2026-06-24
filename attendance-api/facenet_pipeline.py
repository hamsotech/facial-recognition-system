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

# Import các service cốt lõi từ thư mục app.services
from app.services.yolo_detector import detect_person, crop_person
from app.services.mtcnn_alignment import align_face
from app.services.facenet_service import get_embedding
from app.services.similarity_service import cosine_similarity

# ══════════════════════════════════════════════════════════════════
# CẤU HÌNH HỆ THỐNG
# ══════════════════════════════════════════════════════════════════
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "attendance_db",   # Tên database PostgreSQL
    "user":     "postgres",
    "password": "312005",          # Password thật của bạn
}

SIMILARITY_THRESHOLD = 0.65  # Ngưỡng cosine similarity cho FaceNet (thường từ 0.60 - 0.70)
SNAPSHOT_COOLDOWN    = 3     # Giây chờ giữa 2 lần chụp snapshot
CAMERA_INDEX         = 0     # 0 = webcam mặc định

# Thiết bị chạy (GPU CUDA hoặc CPU)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[FaceNet Pipeline] Thiết bị chạy: {DEVICE}")

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
    """
    Tải tất cả FaceNet embeddings hợp lệ từ PostgreSQL.
    """
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
    """
    Quét thư mục dataset_dir cục bộ để trích xuất embeddings.
    Thư mục có cấu trúc:
        dataset/
            Nguyen_Van_A/
                a1.jpg
                a2.jpg
            Tran_Thi_B/
                b1.jpg
    """
    print(f"\n[Local Mode] Đang quét thư mục dataset: {dataset_dir}")
    if not os.path.exists(dataset_dir):
        print(f"[Cảnh báo] Thư mục '{dataset_dir}' không tồn tại. Tạo mới thư mục trống.")
        os.makedirs(dataset_dir, exist_ok=True)
        return {}

    cache_path = os.path.join(dataset_dir, "facenet_local_cache.pkl")
    # Nếu đã có cache, load trực tiếp cho nhanh
    if os.path.exists(cache_path):
        print(f"[Local Mode] Đã tìm thấy tệp cache embeddings. Đang load...")
        try:
            with open(cache_path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"[Cảnh báo] Lỗi khi load cache: {e}. Tiến hành trích xuất lại.")

    registered = {}
    subdirs = [d for d in os.listdir(dataset_dir) if os.path.isdir(os.path.join(dataset_dir, d))]

    for subdir in subdirs:
        student_name = subdir
        student_folder = os.path.join(dataset_dir, subdir)
        images = [f for f in os.listdir(student_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        embeddings_list = []
        for img_name in images:
            img_path = os.path.join(student_folder, img_name)
            try:
                # 1. Phát hiện người bằng YOLOv8
                img, persons = detect_person(img_path)
                if not persons:
                    continue
                
                # 2. Lấy người đầu tiên và căn chỉnh khuôn mặt bằng MTCNN
                roi = crop_person(img, persons[0])
                face_tensor = align_face(roi)
                
                if face_tensor is not None:
                    # 3. Trích xuất FaceNet embedding
                    emb = get_embedding(face_tensor)
                    if emb is not None:
                        embeddings_list.append(emb.numpy())
            except Exception as e:
                print(f"Lỗi khi trích xuất {img_path}: {e}")

        if embeddings_list:
            # Lấy trung bình cộng các vector ảnh của cùng một người để tạo vector đại diện tối ưu nhất
            mean_embedding = np.mean(embeddings_list, axis=0)
            # Chuẩn hóa L2 norm
            mean_embedding = mean_embedding / np.linalg.norm(mean_embedding)
            
            # Tạo UUID ngẫu nhiên cho Local Mode
            sid = str(uuid.uuid4())
            registered[sid] = {
                "full_name": student_name.replace("_", " "),
                "student_code": student_name,
                "research_id": "",
                "embedding": mean_embedding
            }
            print(f"  ✓ Đã đăng ký thành công: {student_name} ({len(embeddings_list)} ảnh)")

    # Lưu cache lại
    if registered:
        with open(cache_path, "wb") as f:
            pickle.dump(registered, f)
        print(f"[Local Mode] Đã lưu cache embeddings tại {cache_path}")

    return registered

# ══════════════════════════════════════════════════════════════════
# HÀM SO SÁNH EMBEDDING TÌM KẾT QUẢ TỐT NHẤT
# ══════════════════════════════════════════════════════════════════
def find_best_match(query_emb: np.ndarray, registered: dict, enrolled_ids: set = None):
    """
    So sánh độ tương đồng cosine giữa query_emb với cơ sở dữ liệu.
    Nếu enrolled_ids được truyền, chỉ so sánh với những sinh viên thuộc danh sách này.
    """
    best_id   = None
    best_info = None
    best_sim  = -1.0

    for sid, info in registered.items():
        # Lọc theo danh sách lớp nếu ở chế độ PostgreSQL
        if enrolled_ids is not None and sid not in enrolled_ids:
            continue

        sim = cosine_similarity(query_emb, info["embedding"])
        if sim > best_sim:
            best_sim  = sim
            best_id   = sid
            best_info = info

    if best_sim >= SIMILARITY_THRESHOLD:
        return best_id, best_info, best_sim
    return None, None, best_sim

# ══════════════════════════════════════════════════════════════════
# XỬ LÝ FRAME CAMERA (SNAPSHOT)
# ══════════════════════════════════════════════════════════════════
def process_frame(frame: np.ndarray):
    """
    Xử lý 1 khung hình camera: Phát hiện người -> Trích xuất mặt -> Tính embedding
    """
    # 1. Phát hiện người bằng YOLOv8
    image, persons = detect_person(frame)
    if not persons:
        return None, None

    for person in persons:
        # 2. Cắt vùng ROI chứa người
        roi = crop_person(image, person)

        # 3. Căn chỉnh khuôn mặt bằng MTCNN
        face_tensor = align_face(roi)
        if face_tensor is not None:
            # 4. Trích xuất FaceNet Embedding
            embedding = get_embedding(face_tensor)
            if embedding is not None:
                # Trả về embedding dạng NumPy array và box người
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
            
            # Kiểm tra session học
            session_info = get_session_info(conn, session_id)
            print(f"[Session] Lớp: {session_info['class_code']} - {session_info['subject_name']}")
            
            # Lấy danh sách SV của lớp
            enrolled_ids = get_enrolled_students(conn, session_id)
            print(f"[Session] Sĩ số lớp: {len(enrolled_ids)} sinh viên")
            
            # Load embeddings
            registered = load_registered_embeddings_db(conn)
        except Exception as e:
            print(f"[Lỗi DB] Không kết nối được cơ sở dữ liệu: {e}")
            print("[Hệ thống] Tự động chuyển về chế độ CỤC BỘ (Local Mode).")
            is_local = True
            registered = load_local_dataset(dataset_dir)

    # Lọc sinh viên hợp lệ (chỉ áp dụng cho chế độ PostgreSQL)
    eligible = registered
    if not is_local and enrolled_ids is not None:
        eligible = {sid: info for sid, info in registered.items() if sid in enrolled_ids}
        print(f"[Database] Số sinh viên thuộc lớp đã có FaceNet embedding: {len(eligible)} người")

    if not eligible:
        print("[!] Không tìm thấy dữ liệu khuôn mặt để đối sánh. Tiến hành tắt chương trình.")
        if conn:
            conn.close()
        return

    # 2. KHỞI CHẠY CAMERA VÀ ĐỐI SÁNH
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[!] Không mở được camera (index={CAMERA_INDEX}). Vui lòng kiểm tra lại thiết bị kết nối.")
        if conn:
            conn.close()
        return

    attended = set()  # Lưu các student_id đã điểm danh trong phiên hiện tại (RAM-only)
    last_snapshot_time = 0.0

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

        # ── KIỂM TRA CAMERA ĐÓNG BĂNG / ẢNH TĨNH GIẢ LẬP ──
        if prev_frame is not None:
            # Nếu hai khung hình giống hệt nhau (chênh lệch trung bình = 0)
            diff = cv2.absdiff(frame, prev_frame)
            mean_diff = np.mean(diff)
            if mean_diff == 0.0:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] [LỖI] Phát hiện luồng camera bị đóng băng hoặc sử dụng ảnh tĩnh làm đầu vào!")
                cv2.putText(display, "ERROR: STATIC INPUT FEED!", (15, 100), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow("FaceNet - Diem Danh Tu Dong", display)
                prev_frame = frame.copy()
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                continue

        prev_frame = frame.copy()

        # Real-time preview: Vẽ box xanh lá cho tất cả mọi người phát hiện được bằng YOLOv8
        _, persons = detect_person(frame)
        for person in persons:
            cv2.rectangle(display, 
                          (person["x1"], person["y1"]), 
                          (person["x2"], person["y2"]), 
                          (0, 255, 0), 2)

        # Xử lý snapshot sau mỗi khoảng cooldown (SNAPSHOT_COOLDOWN)
        if persons and (now - last_snapshot_time >= SNAPSHOT_COOLDOWN):
            last_snapshot_time = now
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{ts}] Phát hiện người -> Đang chụp chuỗi khung hình để kiểm tra tính sống động (Liveness Check)...")

            # ── CHỤP CHUỖI 3 KHUNG HÌNH (Liveness Sequence) ──
            frames_seq = [frame.copy()]
            for _ in range(2):
                time.sleep(0.12)  # Đợi 120ms giữa các frame
                ret_seq, frame_seq = cap.read()
                if ret_seq:
                    frames_seq.append(frame_seq)
                else:
                    frames_seq.append(frame.copy())

            # Căn chỉnh khuôn mặt trên tất cả các khung hình đã chụp
            aligned_faces = []
            person_box = persons[0]  # Lưu box người để vẽ nhãn
            
            for f in frames_seq:
                _, persons_seq = detect_person(f)
                if persons_seq:
                    roi_seq = crop_person(f, persons_seq[0])
                    face_tensor_seq = align_face(roi_seq)
                    if face_tensor_seq is not None:
                        # Đổi tensor FaceNet (3, 160, 160) về ảnh grayscale numpy [0, 255]
                        face_np = face_tensor_seq.permute(1, 2, 0).cpu().numpy()
                        face_np = ((face_np * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
                        face_gray = cv2.cvtColor(face_np, cv2.COLOR_RGB2GRAY)
                        aligned_faces.append(face_gray)

            # ── KIỂM TRA LIVENESS (CHỐNG GIẢ MẠO ẢNH TĨNH) ──
            is_spoof = False
            mean_mad = 0.0
            
            if len(aligned_faces) == 3:
                # Tính độ chênh lệch tuyệt đối trung bình (MAD) giữa các ảnh đã căn chỉnh
                diff1 = cv2.absdiff(aligned_faces[0], aligned_faces[1])
                diff2 = cv2.absdiff(aligned_faces[1], aligned_faces[2])
                mad1 = np.mean(diff1)
                mad2 = np.mean(diff2)
                mean_mad = (mad1 + mad2) / 2.0
                
                # Ngưỡng chống giả mạo ảnh tĩnh:
                # Nếu ảnh tĩnh (ảnh in trên giấy/điện thoại), sau khi căn chỉnh mắt
                # các chi tiết sẽ trùng khít hoàn toàn (chỉ lệch do nhiễu cảm biến < 1.4).
                # Người thật sẽ luôn có chuyển động mắt nhấp nháy, thở, hoặc cơ mặt (MAD >= 1.4).
                if mean_mad < 1.4:
                    is_spoof = True
            else:
                print(f"[{ts}] Không trích xuất đủ khuôn mặt từ chuỗi khung hình (bỏ qua liveness check).")
                continue

            if is_spoof:
                print(f"[{ts}] [LỖI] PHÁT HIỆN SỬ DỤNG ẢNH TĨNH GIẢ MẠO! Độ biến thiên MAD: {mean_mad:.4f}")
                label = "LOI: ANH TINH GIA MAO!"
                color = (0, 0, 255)  # Màu đỏ cảnh báo
                
                # Ghi nhận lỗi giả mạo lên màn hình
                if person_box is not None:
                    cv2.rectangle(display, 
                                  (person_box["x1"], person_box["y1"]), 
                                  (person_box["x2"], person_box["y2"]), 
                                  color, 3)
                    cv2.putText(display, label, 
                                (person_box["x1"], max(person_box["y1"] - 10, 20)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
                continue

            print(f"[{ts}] ✓ Liveness Check thông qua. Độ biến thiên MAD: {mean_mad:.4f}. Tiến hành đối sánh...")

            # ── TIẾN HÀNH ĐỐI SÁNH EMBEDDING (KHI LÀ NGƯỜI THẬT) ──
            # Lấy khuôn mặt cuối cùng trong chuỗi để nhận diện
            last_roi = crop_person(frames_seq[-1], persons[0])
            last_face_tensor = align_face(last_roi)
            
            if last_face_tensor is None:
                print(f"[{ts}] Không tìm thấy khuôn mặt ở khung hình cuối.")
                continue
                
            embedding_tensor = get_embedding(last_face_tensor)
            if embedding_tensor is None:
                print(f"[{ts}] Không trích xuất được FaceNet embedding.")
                continue
                
            query_emb = embedding_tensor.numpy()

            # Đối sánh tìm sinh viên khớp nhất
            matched_id, matched_info, similarity = find_best_match(
                query_emb, eligible, enrolled_ids
            )
            del query_emb  # Giải phóng vector tạm khỏi RAM

            # Xử lý nhãn hiển thị và logic điểm danh
            if matched_id is None:
                label = f"UNKNOWN (sim={similarity:.3f})"
                color = (0, 0, 255)  # Màu đỏ (Không khớp)
                print(f"[{ts}] UNKNOWN — Độ tương đồng tốt nhất: {similarity:.4f}")
            
            elif matched_id in attended:
                name = matched_info["full_name"]
                code = matched_info["student_code"]
                label = f"{name} ({code}) - Attended"
                color = (0, 165, 255)  # Màu cam (Đã điểm danh rồi)
                print(f"[{ts}] Sinh viên {name} ({code}) đã điểm danh trước đó.")
            
            else:
                name = matched_info["full_name"]
                code = matched_info["student_code"]
                label = f"{name} ({code}) {similarity:.3f}"
                color = (0, 255, 0)  # Màu xanh lá (Điểm danh thành công)
                print(f"[{ts}] ✓ PRESENT: {name} | Mã số: {code} | Độ khớp: {similarity:.4f}")

                # Điểm danh thành công: Lưu vào Postgres (nếu không ở chế độ local)
                if not is_local and conn is not None:
                    try:
                        record_attendance_db(conn, session_id, matched_id, similarity)
                        print("       → Đã lưu kết quả điểm danh vào Database.")
                    except Exception as db_err:
                        print(f"       [Lỗi DB] Không ghi được điểm danh: {db_err}")

                # Thêm vào danh sách đã điểm danh trong phiên
                attended.add(matched_id)

            # Vẽ nhãn nhận diện trên màn hình
            if person_box is not None:
                cv2.rectangle(display, 
                              (person_box["x1"], person_box["y1"]), 
                              (person_box["x2"], person_box["y2"]), 
                              color, 3)
                cv2.putText(display, label, 
                            (person_box["x1"], max(person_box["y1"] - 10, 20)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Hiển thị số lượng điểm danh ở góc màn hình
        cv2.putText(display, f"Diem danh: {len(attended)}/{len(eligible)}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(display, f"{session_info['class_code']} | Q=Thoat", 
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        cv2.imshow("FaceNet - Diem Danh Tu Dong", display)
        
        # Nhấn phím 'q' để dừng camera
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("\n[Hệ thống] Người dùng yêu cầu thoát.")
            break

    # DỌN DẸP BỘ NHỚ VÀ ĐÓNG KẾT NỐI
    cap.release()
    cv2.destroyAllWindows()
    attended.clear()
    registered.clear()
    if conn:
        conn.close()
    print("\n[Hệ thống] Đã kết thúc phiên nhận diện và giải phóng thiết bị.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hệ thống điểm danh khuôn mặt bằng mô hình FaceNet")
    parser.add_argument("session_id", nargs="?", default=None, help="UUID phiên học trong database (PostgreSQL)")
    parser.add_argument("--local", action="store_true", help="Chạy chế độ cục bộ không kết nối PostgreSQL")
    parser.add_argument("--dataset", default="dataset", help="Đường dẫn đến thư mục chứa ảnh đối sánh cục bộ")
    
    args = parser.parse_args()
    
    if args.local or args.session_id is None:
        run_pipeline(is_local=True, dataset_dir=args.dataset)
    else:
        # Validate định dạng UUID trước khi chạy
        try:
            uuid.UUID(args.session_id.strip())
            run_pipeline(session_id=args.session_id.strip(), is_local=False, dataset_dir=args.dataset)
        except ValueError:
            print(f"[Lỗi] session_id không đúng định dạng UUID: '{args.session_id}'")
            print("Chạy ở chế độ local bằng cách truyền: python facenet_pipeline.py --local")
            sys.exit(1)
