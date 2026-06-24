from ultralytics import YOLO
import cv2
import numpy as np

# Load model một lần
model = YOLO("yolov8n.pt")


def detect_person(image_or_path):
    """
    Phát hiện người trong ảnh hoặc frame camera.
    image_or_path: có thể là đường dẫn ảnh (str) hoặc numpy array (BGR frame)
    """
    if isinstance(image_or_path, str):
        image = cv2.imread(image_or_path)
        if image is None:
            raise FileNotFoundError(f"Không tìm thấy ảnh tại: {image_or_path}")
    elif isinstance(image_or_path, np.ndarray):
        image = image_or_path.copy()
    else:
        raise ValueError("Đầu vào phải là đường dẫn ảnh (str) hoặc mảng NumPy")

    results = model.predict(
        source=image,
        conf=0.5,
        verbose=False
    )

    persons = []

    for result in results:
        for box in result.boxes:
            cls = int(box.cls[0])
            # Chỉ lấy class person (class 0 trong COCO dataset)
            if cls != 0:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            persons.append({
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2
            })

    return image, persons


def crop_person(image, person):
    """
    Cắt vùng ROI của người từ ảnh gốc.
    """
    h, w = image.shape[:2]
    # Tránh tọa độ vượt quá biên ảnh
    x1 = max(0, person["x1"])
    y1 = max(0, person["y1"])
    x2 = min(w, person["x2"])
    y2 = min(h, person["y2"])
    return image[y1:y2, x1:x2]