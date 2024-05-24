import time, sys
from imagezmq import SerializingContext
from camera import Zero_Camera
from zmq import REP


class Server():

    def __init__(self):
        context = SerializingContext()
        self.socket = context.socket(socket_type=REP)  # REP (REPLY) socket for sending replies to clients
        self.socket.bind("tcp://*:5555")

        print("[#] Server Ready!")

    def receive_msg(self):
        return self.socket.recv().decode()

    def send_jpg(self, msg, img_data):
        """Send a jpg buffer with a text message.

        Sends a jpg bytestring of an OpenCV image.
        Also sends text msg, often the image name.

        Arguments:
          msg: image name or text message.
          jpg_buffer: jpg buffer of compressed image to be sent.
        """
        self.socket.send_jpg(msg, img_data, copy=False)       

    def __del__(self):
        self.socket.close()


if __name__ == "__main__":
    ser = Server()
    cam = Zero_Camera()

    try:
        while True:
            msg = ser.receive_msg()

            start = time.time()
            img_data = cam.get_buffer_data()
            comp_time = time.time() - start 

            ser.send_jpg(f"desired pos 30 deg (comp_t: {comp_time:.3f})", img_data)

    except (KeyboardInterrupt, SystemExit):
        print('Exit due to keyboard interrupt')
    except Exception as ex:
        print('Python error with no Exception handler:')
        print('Traceback error:', ex)
    finally:
        sys.exit()
