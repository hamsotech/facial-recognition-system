import requests

BACKEND_API_URL = 'http://localhost:8080/api/attendance'

def mark_attendance(student_id, session_id, confidence_score):
    """
    Gọi REST API lưu xuống cơ sở dữ liệu.
    """
    try:
        response = requests.post(
            BACKEND_API_URL,
            json={
                'studentId': student_id,
                'sessionId': session_id,
                'confidence': float(confidence_score)
            }
        )
        if response.status_code == 200:
            return True
        else:
            print(f"[API] Backend từ chối điểm danh - Code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[API] Lỗi kết nối tới Backend: {e}")
        return False
