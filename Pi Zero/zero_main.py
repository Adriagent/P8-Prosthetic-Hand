import time

from camera import Zero_Camera
from controller import Controller as Controller
from server import Server



def do_command(ctl:Controller, command:str):
    
    try:
        if not command or command.casefold() == "none":
            output = "[#]: None"
        else:
            output = eval(f"ctl.{command}")
    except Exception as e:
        output = f"[!]: Wrong Command! '{command}' -> {e}"
    
    return output 
        


if __name__ == "__main__":
    try:
        ser = Server()
        cam = Zero_Camera()
        ctl = Controller(5, info=False)
        print("[#]: Server ready! Waiting for client...")

        while True:
            start = time.time()
            img_data = cam.get_buffer_data()
            cam_t = time.time() - start
            
            command = ser.receive_msg()
            
            start = time.time()
            result = do_command(ctl, command)
            eval_t = time.time()-start

            msg = f"{result} (cam_t: {cam_t:.3f} eval_t: {eval_t:.3f})"
            ser.send_jpg(msg, img_data)

    except KeyboardInterrupt:
        print('Exit due to keyboard interrupt')
    except Exception as ex:
        print('Python error with no Exception handler:')
        print('Traceback error:', ex)
    finally:
        cam.__del__()