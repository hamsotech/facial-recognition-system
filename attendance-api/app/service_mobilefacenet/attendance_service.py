import requests

BACKEND_API_URL = 'http://localhost:8080/api/attendance'

def mark_attendance(student_id, session_id, confidence_score):
    try:
        response = requests.post(
            BACKEND_API_URL,
            json={
                'studentId': student_id,
                'sessionId': session_id,
                'confidence': float(confidence_score)
            }
        )
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"[API Error] Backend không phản hồi: {e}")
        return False