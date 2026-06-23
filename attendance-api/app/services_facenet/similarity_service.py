import torch
import torch.nn.functional as F


def cosine_similarity(embedding1, embedding2):
    """
    embedding1: Tensor (512,)
    embedding2: Tensor (512,)
    """

    score = F.cosine_similarity(
        embedding1.unsqueeze(0),
        embedding2.unsqueeze(0)
    )

    return score.item()