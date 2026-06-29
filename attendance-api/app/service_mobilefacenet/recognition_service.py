"""
service_mobilefacenet/recognition_service.py — MobileFaceNet Pipeline
════════════════════════════════════════════════════════════════════════
Dùng chung: YOLO, MTCNN, Similarity, Attendance từ app.shared
Riêng biệt: MobileFaceNet ONNX embedding (app.service_mobilefacenet.mobilefacenet_service)
"""

import time
import logging
import cv2

from app.shared import detect_person, crop_person, align_face, cosine_similarity, mark_attendance
from app.service_mobilefacenet.mobilefacenet_service import get_embedding

logger = logging.getLogger(__name__)

# MobileFaceNet thường cần threshold thấp hơn ArcFace/FaceNet do vector ngắn hơn
THRESHOLD         = 0.55
CAMERA_INDEX      = 0
SNAPSHOT_COOLDOWN = 3.0


def start_live_attendance(session_id: str, registered_students: dict):
    """
    Chạy pipeline điểm danh realtime bằng MobileFaceNet (nhẹ, phù hợp edge device).

    Args:
        session_id:          UUID phiên học.
        registered_students: Dict { student_id: {"embedding": np.ndarray, ...} }
    """
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        logger.error("[MobileFaceNet] Không thể mở camera.")
        return

    attended_set = set()
    last_snapshot_time = 0.0
    logger.info(f"[MobileFaceNet] Bắt đầu điểm danh (Session: {session_id})")

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
                    del roi

                    if face_tensor is not None:
                        query_emb = get_embedding(face_tensor)
                        del face_tensor

                        best_sim, best_id = -1.0, None
                        for sid, info in registered_students.items():
                            sim = cosine_similarity(query_emb, info["embedding"])
                            if sim > best_sim:
                                best_sim, best_id = sim, sid
                        del query_emb

                        if best_sim >= THRESHOLD:
                            label = f"{best_id} (OK)" if best_id not in attended_set else "ĐÃ ĐIỂM DANH"
                            color = (0, 255, 0) if best_id not in attended_set else (0, 165, 255)
                            if best_id not in attended_set:
                                logger.info(f"[✓] {best_id} — sim={best_sim:.3f}")
                                mark_attendance(best_id, session_id, best_sim)
                                attended_set.add(best_id)
                        else:
                            label, color = "UNKNOWN", (0, 0, 255)

                        cv2.putText(display, label,
                                    (person["x1"], person["y1"] - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            except ValueError as ve:
                logger.warning(str(ve))
                break

            del snapshot
            last_snapshot_time = now

        cv2.putText(display, f"SL Hiện Diện: {len(attended_set)}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.imshow("Live Attendance (MobileFaceNet)", display)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    attended_set.clear()


if __name__ == "__main__":
    start_live_attendance("test_session_mobilefacenet", {})