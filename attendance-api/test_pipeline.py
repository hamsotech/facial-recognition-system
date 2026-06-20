from app.services.yolo_detector import (
    detect_person,
    crop_person
)

from app.services.mtcnn_alignment import (
    align_face
)

from app.services.facenet_service import (
    get_embedding
)

image, persons = detect_person(
    "attendance-api/classroom.jpg"
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