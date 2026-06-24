import requests

def mark_attendance(student_id, session_id):
    requests.post(
        'http://localhost:8080/api/attendance',
        json={'studentId': student_id, 'sessionId': session_id}
    )
