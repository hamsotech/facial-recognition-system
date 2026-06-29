import cv2
import time
from yolo_detector import detect_person, crop_person
from mtcnn_alignment import align_face
from arcface_service import get_embedding
from similarity_service import cosine_similarity
from attendance_service import mark_attendance

THRESHOLD = 0.5
CAMERA_INDEX = 0
SNAPSHOT_COOLDOWN = 3.0  # Giây

def start_live_attendance(session_id, registered_students):
    """
    registered_students là dictionary có dạng: 
    { "student_id_1": {"embedding": [vector...]}, ... }
    (Sẽ được load thông qua API từ Database lúc bắt đầu phiên)
    """
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("[!] Lỗi: Không thể mở camera.")
        return

    attended_set = set()
    last_snapshot_time = 0.0

    print(f"\n[Hệ thống] Bắt đầu điểm danh Camera (Session: {session_id})")

    while True:
        ret, frame = cap.read()
        if not ret: break

        display = frame.copy()
        now = time.time()

        # Chỉ trích xuất AI sau mỗi chu kỳ Cooldown
        if now - last_snapshot_time >= SNAPSHOT_COOLDOWN:
            # 1. Bắt snapshot tạm vào RAM
            snapshot = frame.copy()
            
            try:
                # 2. Quét YOLO trên snapshot. Chặn ảnh tĩnh nằm ở đây
                persons = detect_person(snapshot)
                
                for person in persons:
                    # 3. Cắt mặt và nén dữ liệu
                    roi = crop_person(snapshot, person)
                    face_tensor = align_face(roi)
                    del roi  # [RAM CLEAR] Xóa hình ảnh ROI
                    
                    if face_tensor is not None:
                        # 4. Trích vector AI
                        query_emb = get_embedding(face_tensor)
                        del face_tensor  # [RAM CLEAR] Xóa tensor mặt
                        
                        # 5. So sánh với danh sách đăng ký
                        best_sim = -1.0
                        best_id = None
                        
                        for sid, info in registered_students.items():
                            sim = cosine_similarity(query_emb, info["embedding"])
                            if sim > best_sim:
                                best_sim = sim
                                best_id = sid
                                
                        del query_emb  # [RAM CLEAR] Xóa vector chụp từ camera
                        
                        # 6. Gửi API lưu DB nếu khớp
                        if best_sim >= THRESHOLD:
                            if best_id not in attended_set:
                                print(f"[✓] {best_id} - Khớp: {best_sim:.3f}")
                                mark_attendance(best_id, session_id, best_sim)
                                attended_set.add(best_id)
                                cv2.putText(display, f"{best_id} (OK)", (person["x1"], person["y1"]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            else:
                                cv2.putText(display, "DA DIEM DANH", (person["x1"], person["y1"]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                        else:
                            cv2.putText(display, "UNKNOWN", (person["x1"], person["y1"]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            except ValueError as ve:
                print(ve)
                break
            
            # 7. [RAM CLEAR] Giải phóng hoàn toàn ảnh chụp tạm khỏi bộ nhớ
            del snapshot
            last_snapshot_time = now

        # Hiển thị GUI
        cv2.putText(display, f"SL Hien Dien: {len(attended_set)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.imshow("Live Attendance (ArcFace)", display)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Dọn dẹp thiết bị ngoại vi
    cap.release()
    cv2.destroyAllWindows()
    attended_set.clear()

# Khối Test giả lập
if __name__ == "__main__":
    # Test với ID phiên giả và không có dữ liệu gốc
    start_live_attendance("test_session_123", {})