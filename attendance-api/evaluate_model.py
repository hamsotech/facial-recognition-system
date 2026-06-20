import os

import cv2

from app.services.mtcnn_alignment import align_face

from app.services.facenet_service import get_embedding

from app.services.similarity_service import cosine_similarity

from app.services.threshold_service import predict


dataset = "dataset"

threshold = 0.7

TP = 0

TN = 0

FP = 0

FN = 0

students = os.listdir(dataset)

for student in students:

    folder = os.path.join(
        dataset,
        student
    )

    images = os.listdir(folder)

    if len(images) < 2:
        continue

    img1 = cv2.imread(
        os.path.join(
            folder,
            images[0]
        )
    )

    img2 = cv2.imread(
        os.path.join(
            folder,
            images[1]
        )
    )

    face1 = align_face(img1)

    face2 = align_face(img2)

    if face1 is None or face2 is None:
        continue

    emb1 = get_embedding(face1)

    emb2 = get_embedding(face2)

    score = cosine_similarity(
        emb1,
        emb2
    )

    if predict(score, threshold):

        TP += 1

    else:

        FN += 1


print("TP =", TP)

print("FN =", FN)