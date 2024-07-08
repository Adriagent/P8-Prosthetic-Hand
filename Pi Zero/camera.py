import time, io
from PIL import Image
from picamera2 import Picamera2 # type: ignore

class Zero_Camera():

    def __init__(self):
        self.picam2 = Picamera2()
        self.set_camera_config() # "YUV420"

        self.last_frame = None
        self.last_buffer_data = None

    def set_camera_config(self, format="BGR888", size=(640,480), quality=50):
        config = self.picam2.create_video_configuration()
        config["main"]["size"]          = size
        config["main"]["format"]        = format
        self.picam2.options['quality']  = quality  # JPEG quality (0 - 100)

        self.picam2.configure(config)
        self.picam2.start()

        time.sleep(1)
        print("[#]: Camera Ready!")

    def get_frame(self):
        self.last_frame = self.picam2.capture_array()
        return self.last_frame

    def get_buffer_data(self):
        buffer = io.BytesIO()
        self.picam2.capture_file(buffer, format='jpeg')
        buffer.seek(0)
        self.last_buffer_data = buffer.getvalue()

        return self.last_buffer_data
    
    def __del__(self):
        if self.picam2.started:
            self.picam2.stop()
            

if __name__ == "__main__":
    cam = Zero_Camera()

    try:
        while True:
            start = time.time()
            img = cam.get_buffer_data()  # Adjust based on whether you need the buffer data or raw frame
            print(f"[#] {len(img)/1024:.2f} KB {time.time() - start:.3f}")

    except KeyboardInterrupt:
        pass

    finally:
        cam.picam2.stop()
