from facenet_pytorch import MTCNN
from PIL import Image
import cv2

mtcnn = MTCNN(
    image_size=160,
    margin=20,
    keep_all=False
)


def align_face(person_image):
    """
    Phát hiện khuôn mặt và chuẩn hóa thành tensor (3, 160, 160) cho FaceNet.
    """
    if person_image is None or person_image.size == 0:
        return None

    try:
        rgb = cv2.cvtColor(
            person_image,
            cv2.COLOR_BGR2RGB
        )
        pil_image = Image.fromarray(rgb)
        face_tensor = mtcnn(pil_image)
        return face_tensor
    except Exception as e:
        print(f"[MTCNN] Lỗi khi xử lý căn chỉnh khuôn mặt: {e}")
        return None