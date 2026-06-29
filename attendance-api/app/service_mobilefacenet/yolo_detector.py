from ultralytics import YOLO
import cv2
import numpy as np
# Load model YOLO một lần
model = YOLO("yolov8n.pt")

def detect_person(frame):
    """
    Phát hiện người trong frame. Chặn đọc file ảnh tĩnh.
    """
    if not isinstance(frame, np.ndarray):
        raise ValueError("[Bảo Mật] Mô hình MobileFaceNet từ chối ảnh tĩnh. Chỉ nhận luồng Camera.")

    image = frame.copy()
    results = model.predict(source=image, conf=0.5, verbose=False)
    persons = []

    for result in results:
        for box in result.boxes:
            if int(box.cls[0]) != 0:  # Class 0 là người
                continue
            
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            persons.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})
            
    del image # Xóa copy
    return persons

def crop_person(image, person, margin=0.10):
    h, w = image.shape[:2]
    x1, y1, x2, y2 = person["x1"], person["y1"], person["x2"], person["y2"]
    
    bw, bh = x2 - x1, y2 - y1
    x1 = max(0, int(x1 - bw * margin))
    y1 = max(0, int(y1 - bh * margin))
    x2 = min(w, int(x2 + bw * margin))
    y2 = min(h, int(y2 + bh * margin))
    
    return image[y1:y2, x1:x2]