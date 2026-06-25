from facenet_pytorch import MTCNN
from PIL import Image
import cv2
import torch

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

mtcnn = MTCNN(
    image_size=112,  # MobileFaceNet tối ưu nhất với size 112x112
    margin=0,
    min_face_size=20,
    thresholds=[0.6, 0.7, 0.7],
    factor=0.709,
    post_process=True,
    device=DEVICE,
    keep_all=False
)

def align_face(person_image):
    if person_image is None or person_image.size == 0:
        return None
    try:
        rgb = cv2.cvtColor(person_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)   # MTCNN cần PIL Image, không phải numpy
        face_tensor = mtcnn(pil_image)
        return face_tensor
    except Exception as e:
        print(f"[MTCNN] Lỗi căn chỉnh: {e}")
        return None