import cv2


class CSICamera:

    def __init__(self, sensor_id=0, width=1280, height=720, flip_method=2):
        # SỬA: Thêm định dạng format=NV12 vào ngay sau height để tránh lỗi kết nối GStreamer
        pipeline = (
            f"nvarguscamerasrc sensor-id={sensor_id} ! "
            f"video/x-raw(memory:NVMM),width={width},height={height},format=NV12,framerate=30/1 ! "
            f"nvvidconv flip-method={flip_method} ! "
            "video/x-raw,format=BGRx ! "
            "videoconvert ! "
            "video/x-raw,format=BGR ! "
            "appsink drop=true max-buffers=1 sync=false"
        )

        self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

        # CẢI TIẾN: Kiểm tra và cảnh báo ngay khi khởi tạo nếu cam lỗi
        if not self.cap.isOpened():
            print(
                f"[CSICamera LỖI] Không thể kết nối với Camera CSI qua GStreamer (sensor-id={sensor_id})."
            )
            print(
                " -> Hãy kiểm tra lại cáp ruy-băng hoặc chạy: sudo systemctl restart nvargus-daemon"
            )

    def isOpened(self):
        return self.cap.isOpened()

    def read(self):
        return self.cap.read()

    def release(self):
        self.cap.release()