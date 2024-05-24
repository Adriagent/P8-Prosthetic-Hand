import time, io
from PIL import Image
from picamera2 import Picamera2 # type: ignore

class Zero_Camera():

    def __init__(self):
        self.picam2 = Picamera2()
        self.buffer = io.BytesIO()  # Reusable buffer
        
        self.set_camera_config("YUV420")        
        # self.set_camera_config()        

    def set_camera_config(self, format="YUV420", size=(640, 480)):
        config = self.picam2.create_video_configuration()
        config["main"]["size"] = size
        config["main"]["format"] = format
        config["controls"]['FrameRate'] = 120

        self.picam2.configure(config)
        self.picam2.start()

    def get_frame(self):
        return self.picam2.capture_array()

    def get_buffer_data(self):
        img = self.picam2.capture_array()
        image = Image.fromarray(img)
        image.save(self.buffer, format='JPEG', quality=50)
        self.buffer.seek(0)

        return self.buffer.getvalue()
    
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
