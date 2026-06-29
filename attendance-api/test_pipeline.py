from app.service_facenet.yolo_detector import (
    detect_person,
    crop_person
)

from app.service_facenet.mtcnn_alignment import (
    align_face
)

from app.service_facenet.facenet_service import (
    get_embedding
)

import os
img_path = "attendance-api/classroom.jpg"
if not os.path.exists(img_path) and os.path.exists("classroom.jpg"):
    img_path = "classroom.jpg"

image, persons = detect_person(
    img_path
)

print("Persons:", len(persons))

for i, person in enumerate(persons):

    roi = crop_person(
        image,
        person
    )

    face = align_face(
        roi
    )

    if face is None:

        print(
            f"Person {i+1}: No face"
        )

        continue

    embedding = get_embedding(
        face
    )

    print(
        f"Person {i+1}"
    )

    print(
        embedding.shape
    )