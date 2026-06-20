import torch
from facenet_pytorch import InceptionResnetV1

facenet = InceptionResnetV1(
    pretrained="vggface2"
).eval()


def get_embedding(face_tensor):

    if face_tensor is None:
        return None

    face_tensor = face_tensor.unsqueeze(0)

    with torch.no_grad():
        embedding = facenet(face_tensor)

    return embedding.squeeze(0)