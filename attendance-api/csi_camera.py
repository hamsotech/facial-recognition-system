import cv2


class CSICamera:

    def __init__(self, sensor_id=0, width=1280, height=720, flip_method=2):

        pipeline = (
            f"nvarguscamerasrc sensor-id={sensor_id} ! "
            f"video/x-raw(memory:NVMM),width={width},height={height},framerate=30/1 ! "
            f"nvvidconv flip-method={flip_method} ! "
            "video/x-raw,format=BGRx ! "
            "videoconvert ! "
            "video/x-raw,format=BGR ! "
            "appsink drop=true max-buffers=1 sync=false"
        )

        self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

    def isOpened(self):
        return self.cap.isOpened()

    def read(self):
        return self.cap.read()

    def release(self):
        self.cap.release()