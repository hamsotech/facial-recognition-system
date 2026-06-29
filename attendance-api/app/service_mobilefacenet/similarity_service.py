import numpy as np
from scipy.spatial.distance import cosine as cosine_distance

def cosine_similarity(emb1, emb2):
    emb1 = np.array(emb1).flatten()
    emb2 = np.array(emb2).flatten()
    return 1.0 - cosine_distance(emb1, emb2)