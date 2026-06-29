import os
import numpy as np
import cv2
import torch
import onnxruntime as ort

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Đảm bảo bạn đã lưu model tại đường dẫn này
ARCFACE_MODEL_PATH = os.path.join(
    os.path.expanduser("~"),
    ".insightface", "models", "buffalo_l", "w600k_r50.onnx"
)

if not os.path.exists(ARCFACE_MODEL_PATH):
    raise FileNotFoundError(f"Không tìm thấy model ArcFace tại: {ARCFACE_MODEL_PATH}")

_ort_providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if DEVICE == "cuda" else ["CPUExecutionProvider"]
_arcface = ort.InferenceSession(ARCFACE_MODEL_PATH, providers=_ort_providers)
_arcface_input = _arcface.get_inputs()[0].name

def get_embedding(face_tensor):
    """
    Chuyển tensor mặt từ MTCNN thành vector 512D.
    """
    if face_tensor is None:
        return None

    # Biến đổi Tensor -> numpy HWC [0,255]
    img = face_tensor.permute(1, 2, 0).cpu().numpy()
    img = (img * 128.0 + 127.5).clip(0, 255).astype(np.uint8)
    
    # Resize chuẩn ArcFace 112x112
    img = cv2.resize(img, (112, 112))
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    img = (img.astype(np.float32) - 127.5) / 128.0
    
    # Chuẩn bị input cho model ONNX
    inp = np.expand_dims(img.transpose(2, 0, 1), axis=0)
    output = _arcface.run(None, {_arcface_input: inp})
    
    return output[0].flatten()