import cv2
import face_recognition

class DlibService:
    def get_embedding(self, face_img):
        rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(rgb)
        if len(encodings) == 0:
            return None
        return encodings[0]

dlib_service = DlibService()
