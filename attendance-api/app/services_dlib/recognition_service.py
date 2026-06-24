import requests
import numpy as np
from similarity_service import cosine_similarity

THRESHOLD = 0.65
SPRING_API = 'http://localhost:8080/api'
