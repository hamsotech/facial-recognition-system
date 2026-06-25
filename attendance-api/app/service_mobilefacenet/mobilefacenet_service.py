import os
import numpy as np
import cv2
import torch
import onnxruntime as ort

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Đường dẫn tới file model ONNX của MobileFaceNet
MOBILEFACENET_MODEL_PATH = os.path.join(os.getcwd(), "models", "MobileFaceNet.onnx")

if not os.path.exists(MOBILEFACENET_MODEL_PATH):
    raise FileNotFoundError(f"Lỗi: Hãy tạo thư mục 'models' và tải file MobileFaceNet.onnx vào đường dẫn: {MOBILEFACENET_MODEL_PATH}")

_ort_providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if DEVICE == "cuda" else ["CPUExecutionProvider"]
_mobilefacenet = ort.InferenceSession(MOBILEFACENET_MODEL_PATH, providers=_ort_providers)
_input_name = _mobilefacenet.get_inputs()[0].name

def get_embedding(face_tensor):
    """
    Chuyển tensor mặt thành vector đặc trưng.
    """
    if face_tensor is None:
        return None

    # MTCNN Tensor -> numpy HWC [0,255]
    img = face_tensor.permute(1, 2, 0).cpu().numpy()
    img = (img * 128.0 + 127.5).clip(0, 255).astype(np.uint8)
    
    # Tiền xử lý riêng cho MobileFaceNet
    img = cv2.resize(img, (112, 112))
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    img = (img.astype(np.float32) - 127.5) / 128.0
    
    inp = np.expand_dims(img.transpose(2, 0, 1), axis=0)
    output = _mobilefacenet.run(None, {_input_name: inp})
    
    return output[0].flatten() # Tùy phiên bản ONNX, vector có thể là 128D hoặc 192D