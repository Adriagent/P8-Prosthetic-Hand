import numpy as np
import sys, cv2, time
from imagezmq import SerializingContext
from zmq import RCVTIMEO, SNDTIMEO, REQ


class Client():

    def __init__(self):
        context = SerializingContext()
        self.socket = context.socket(socket_type=REQ)     # REQ (REQUEST) socket for sending requests
        self.socket.connect("tcp://zero.local:5555")
        self.socket.setsockopt(RCVTIMEO, 5000)          # Receive timeout in milliseconds
        self.socket.setsockopt(SNDTIMEO, 5000)          # Send timeout in milliseconds

        print("[#] Connecting to server...")

    def send_msg(self, msg:str):
        self.socket.send(msg.encode())

    def get_jpg(self) -> tuple[str, np.ndarray]:
        """Receives a jpg buffer and a text msg.

        Receives a jpg bytestring of an OpenCV image.
        Also receives a text msg, often the image name.

        Returns:
          msg: image name or text message.
          img: cv2 image.
        """
        msg, img_bytes = self.socket.recv_jpg()
        # Decode the received JPEG image
        img = cv2.imdecode(np.frombuffer(img_bytes, dtype='uint8'), -1)
        
        # Check if the image is successfully decoded
        if img is None:
            print("Failed to decode image")
            img = np.ones((480,640,3), np.uint8)
            return msg, img

        # Convert YUV420 to RGB
        img_bgr = cv2.cvtColor(img, cv2.COLOR_YUV2BGR_I420)
            
        return msg, img_bgr

    def __del__(self):
        self.socket.close()

if __name__ == "__main__":
    try:    
        cli = Client()

        while True:
            start = time.time()
            cli.send_msg("Set motor 1 to 30 deg")
            msg, img = cli.get_jpg()
            rtt = time.time() - start

            print(f"Received message: {msg} (RTT: {rtt:.3f} s.)") 
            cv2.imshow('Frame', img)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except (KeyboardInterrupt, SystemExit):
        print('Exit due to keyboard interrupt')
    except Exception as ex:
        print('Python error with no Exception handler:')
        print('Traceback error:', ex)
    finally:
        cv2.destroyAllWindows()
        sys.exit()
