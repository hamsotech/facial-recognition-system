from ultralytics import YOLO
import cv2

# Load model một lần
model = YOLO("yolov8n.pt")


def detect_person(image_path):

    image = cv2.imread(image_path)

    if image is None:
        raise FileNotFoundError(image_path)

    results = model.predict(
        source=image,
        conf=0.5,
        verbose=False
    )

    persons = []

    for result in results:

        for box in result.boxes:

            cls = int(box.cls[0])

            # Chỉ lấy class person
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

    return image[
        person["y1"]:person["y2"],
        person["x1"]:person["x2"]
    ]