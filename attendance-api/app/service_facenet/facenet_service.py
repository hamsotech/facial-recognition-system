import torch
from facenet_pytorch import InceptionResnetV1

# Tự động chọn GPU nếu khả dụng
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[FaceNet] Đang sử dụng thiết bị: {device}")

facenet = InceptionResnetV1(
    pretrained="vggface2"
).to(device).eval()


def get_embedding(face_tensor):
    """
    Trích xuất vector đặc trưng (embedding) 512 chiều từ face_tensor.
    """
    if face_tensor is None:
        return None

    # Chuyển tensor sang device tương ứng (CPU hoặc GPU)
    face_tensor = face_tensor.to(device).unsqueeze(0)

    with torch.no_grad():
        embedding = facenet(face_tensor)

    # Trả về tensor trên CPU để dễ dàng thao tác hoặc so sánh sau này
    return embedding.squeeze(0).cpu()