import torch
import numpy as np

def cosine_similarity(embedding1, embedding2):
    """
    Tính toán độ tương đồng Cosine (Cosine Similarity) giữa hai vector đặc trưng.
    Chấp nhận cả PyTorch Tensor và NumPy ndarray.
    """
    # Chuyển đổi sang numpy array nếu là PyTorch Tensor
    if isinstance(embedding1, torch.Tensor):
        embedding1 = embedding1.detach().cpu().numpy()
    if isinstance(embedding2, torch.Tensor):
        embedding2 = embedding2.detach().cpu().numpy()
        
    # Làm phẳng vector (flatten)
    emb1 = embedding1.flatten()
    emb2 = embedding2.flatten()
    
    # Tính cosine similarity bằng numpy
    dot_product = np.dot(emb1, emb2)
    norm_a = np.linalg.norm(emb1)
    norm_b = np.linalg.norm(emb2)
    
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
        
    score = dot_product / (norm_a * norm_b)
    return float(score)