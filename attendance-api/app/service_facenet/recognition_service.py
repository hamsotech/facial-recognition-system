import cv2
import time
from yolo_detector import detect_person, crop_person
from mtcnn_alignment import align_face
from facenet_service import get_embedding
from similarity_service import cosine_similarity
from threshold_service import predict
from attendance_service import mark_attendance

THRESHOLD = 0.7
CAMERA_INDEX = 0
SNAPSHOT_COOLDOWN = 3.0  # Giây

def start_live_attendance(session_id, registered_students):
    """
    registered_students: dict dạng
    { "student_id_1": {"embedding": tensor_or_array}, ... }
    """
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("[!] Lỗi: Không thể mở camera.")
        return

    attended_set = set()
    last_snapshot_time = 0.0

    print(f"\n[Hệ thống] Bắt đầu điểm danh FaceNet (Session: {session_id})")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        display = frame.copy()
        now = time.time()

        if now - last_snapshot_time >= SNAPSHOT_COOLDOWN:
            snapshot = frame.copy()

            try:
                persons = detect_person(snapshot)

                for person in persons:
                    roi = crop_person(snapshot, person)
                    face_tensor = align_face(roi)
                    del roi  # [RAM CLEAR]

                    if face_tensor is not None:
                        query_emb = get_embedding(face_tensor)
                        del face_tensor  # [RAM CLEAR]

                        best_sim = -1.0
                        best_id = None

                        for sid, info in registered_students.items():
                            sim = cosine_similarity(query_emb, info["embedding"])
                            if sim > best_sim:
                                best_sim = sim
                                best_id = sid

                        del query_emb  # [RAM CLEAR]

                        if predict(best_sim, THRESHOLD):
                            if best_id not in attended_set:
                                print(f"[✓] {best_id} - Khớp: {best_sim:.3f}")
                                mark_attendance(best_id, session_id, best_sim)
                                attended_set.add(best_id)
                                cv2.putText(display, f"{best_id} (OK)", (person["x1"], person["y1"] - 10),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                            else:
                                cv2.putText(display, "DA DIEM DANH", (person["x1"], person["y1"] - 10),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                        else:
                            cv2.putText(display, "UNKNOWN", (person["x1"], person["y1"] - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            except ValueError as ve:
                print(ve)
                break

            del snapshot  # [RAM CLEAR]
            last_snapshot_time = now

        cv2.putText(display, f"SL Hien Dien: {len(attended_set)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.imshow("Live Attendance (FaceNet)", display)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    attended_set.clear()


if __name__ == "__main__":
    start_live_attendance("test_session_facenet", {})
