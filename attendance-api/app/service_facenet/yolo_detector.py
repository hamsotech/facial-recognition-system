from ultralytics import YOLO
import cv2
import numpy as np

model = YOLO("yolov8n.pt")

def detect_person(frame):
    """
    Phát hiện người trong frame camera (Chỉ chấp nhận numpy array - Live camera).
    Không chấp nhận đường dẫn ảnh tĩnh (str).
    """
    if not isinstance(frame, np.ndarray):
        raise ValueError("[Bảo mật] Hệ thống chỉ chấp nhận hình ảnh trực tiếp từ camera (RAM). Không hỗ trợ ảnh tĩnh.")

    # Đảm bảo copy frame để không ảnh hưởng đến luồng gốc
    image = frame.copy()

    results = model.predict(source=image, conf=0.5, verbose=False)
    persons = []

    for result in results:
        for box in result.boxes:
            cls = int(box.cls[0])
            if cls != 0: # Chỉ lấy người (class 0)
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            persons.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})
            
    # Xóa ảnh copy khỏi RAM ngay sau khi quét xong bounding box
    del image
    return persons