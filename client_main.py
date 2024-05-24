import time, cv2, sys, numpy as np
from client import Client

if __name__ == "__main__":
    try:
        cli = Client()
        begin = time.time()
        while True:
            start = time.time()

            msg = "get_motor_position()"

            cli.send_msg(msg)
            msg, img = cli.get_jpg()
            cv2.imshow('Frame', img)
            elapsed = time.time() - start

            print(f"Received message: {msg} (elapsed: {elapsed:.3f} s.)")

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
