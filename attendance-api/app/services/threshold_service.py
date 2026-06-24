def predict(score, threshold=0.7):
    """
    score >= threshold
        => cùng người

    score < threshold
        => khác người
    """

    return score >= threshold