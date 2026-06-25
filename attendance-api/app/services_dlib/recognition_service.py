import cv2
import time
import numpy as np
from dlib_service import dlib_service
from similarity_service import cosine_similarity
from attendance_service import mark_attendance

THRESHOLD = 0.65
CAMERA_INDEX = 0
SNAPSHOT_COOLDOWN = 3.0  # Giây

def start_live_attendance(session_id, registered_students):
    """
    registered_students: dict dạng
    { "student_id_1": {"embedding": array_128d}, ... }
    Dlib face_recognition trả về vector 128D.
    """
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("[!] Lỗi: Không thể mở camera.")
        return

    attended_set = set()
    last_snapshot_time = 0.0

    print(f"\n[Hệ thống] Bắt đầu điểm danh Dlib (Session: {session_id})")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        display = frame.copy()
        now = time.time()

        if now - last_snapshot_time >= SNAPSHOT_COOLDOWN:
            snapshot = frame.copy()

            # Dlib tự phát hiện khuôn mặt bên trong get_embedding
            # nên không cần YOLO + MTCNN như ArcFace/FaceNet
            query_emb = dlib_service.get_embedding(snapshot)
            del snapshot  # [RAM CLEAR]

            if query_emb is not None:
                best_sim = -1.0
                best_id = None

                for sid, info in registered_students.items():
                    sim = cosine_similarity(query_emb, info["embedding"])
                    if sim > best_sim:
                        best_sim = sim
                        best_id = sid

                if best_sim >= THRESHOLD:
                    if best_id not in attended_set:
                        print(f"[✓] {best_id} - Độ khớp: {best_sim:.3f}")
                        mark_attendance(best_id, session_id, best_sim)
                        attended_set.add(best_id)
                        cv2.putText(display, f"{best_id} (OK)", (10, 60),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    else:
                        cv2.putText(display, "DA DIEM DANH", (10, 60),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                else:
                    cv2.putText(display, "UNKNOWN", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            last_snapshot_time = now

        cv2.putText(display, f"SL Hien Dien: {len(attended_set)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.imshow("Live Attendance (Dlib)", display)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    attended_set.clear()


if __name__ == "__main__":
    start_live_attendance("test_session_dlib", {})
