
import sys, time

from numpy import interp, round

from motor_MX_28R import MX_28R as Motor
from dynamixel_sdk import PortHandler, GroupSyncRead, COMM_SUCCESS                           # Uses Dynamixel SDK library
from packet_handler_modified_p_2 import Protocol2PacketHandler as Packet_Handler


class Controller:

    # Serial com settings
    BAUD_57600              = 57600             # Raspberry default baudrate : 57600
    BAUD_115200             = 115200            # Raspberry default baudrate : 115200
    BAUD_1M                 = 1_000_000         # Raspberry default baudrate : 1_000_000
    PORT_USB_WI             = 'COM4'            # Port being used on windows (USB)
    PORT_USB_PI             = '/dev/ttyUSB0'    # Port being used on raspi 4 (USB)
    PORT_UART_PI            = '/dev/serial0'    # Port being used on raspi 4 (UART)
    
    # Communication protocol
    PROTOCOL                = 2                 # Dynamixel motors support both 1.0 and 2.0 protocols.

    # Broadcast address
    BROADCAST_ID            = 254               # ID for broadcasting to all the motors

    # MISC
    motors:dict[int,Motor]  = {}
    portHandler             = None
    GIVE_INFO               = True
    groupSyncRead           = None

    def __init__(self, n_motors=1, port=PORT_UART_PI, baud=BAUD_1M, info=True):
        self.GIVE_INFO=info
        self.n_motors = n_motors
        
        self.begin(port=port, baud=baud)
        self.find_motors(n_motors)
        self.config_sync_read()

    def begin(self, port=PORT_UART_PI, baud=BAUD_1M):
        if self.portHandler is not None and self.portHandler.is_open:
            self.portHandler.closePort()

        self.portHandler = PortHandler(port) # Initialize PortHandler instance and Set the port path
        self.packetHandler = Packet_Handler(baud) # Initialize PacketHandler instance.

        if not self.portHandler.openPort():
            print("[E]: Failed to open the port")
            sys.exit()

        if not self.portHandler.setBaudRate(baud):
            print("[E]: Failed to change the baudrate")
            sys.exit()

        print("[i]: Port opened and baud rate set to", baud)

    def set_extra_bytes(self, extra_bytes:int):
        self.packetHandler.extra_bytes = extra_bytes

    def find_motors(self, n_motors=None):
        if n_motors:
            self.n_motors = n_motors

        while len(self.motors) < self.n_motors:
            dxl_data_list, _ = self.packetHandler.broadcastPing(self.portHandler)

            self.motors = {dxl_id: Motor(self.portHandler, self.packetHandler, dxl_id) for dxl_id in sorted(dxl_data_list.keys())}

            if self.motors:
                print(f"[i]: Dynamixel found ID {list(self.motors.keys())}")
            else:
                print("[!]: Cannot not find any motor")
                sys.exit()

    def set_led(self, mode, ids:list[int]=None):
        if ids is None: 
            ids = self.motors

        info = ("DISABLED", "ENABLED")

        succeded = [id for id in ids if self.motors[id].set_led(mode)]
        if succeded and self.GIVE_INFO:
            print(f"[#]: Motor_{succeded}: LED has been {info[mode]}")
        return succeded

    def set_torque(self, mode, ids:list[int]=None):
        if ids is None: 
            ids = self.motors

        info = ("DISABLED", "ENABLED")

        succeded = [id for id in ids if self.motors[id].set_torque(mode)]
        if succeded and self.GIVE_INFO:
            print(f"[#]: Motor_{succeded}: Torque has been {info[mode]}")
        return succeded

    def get_torque(self, ids:list[int]=None):
        if ids is None: 
            ids = list(self.motors.keys())

        torques = [self.motors[id].get_torque() for id in ids]
        if torques and self.GIVE_INFO:
            print(f"[#]: Motor_{ids}: Current torque is = {[torque if torque is not None else None for torque in torques]}")

        return torques

    def set_mode(self, mode, ids:list[int]=None):
        "mode: int -> 0: Position, 1: Velocity, 2: PWM"

        if ids is None: 
            ids = self.motors

        info = ("POSITION", "VELOCITY", "PWM")

        succeded = [id for id in ids if self.motors[id].set_mode(mode)]
        if succeded and self.GIVE_INFO:
            print(f"[#]: Motor_{succeded}: {info[mode]} mode has been set")

        return succeded

    def get_mode(self, ids:list[int]=None):
        if ids is None: 
            ids = list(self.motors.keys())

        info = ("POSITION", "VELOCITY", "PWM")

        modes = [self.motors[id].get_mode() for id in ids]
        if modes and self.GIVE_INFO:
            print(f"[#]: Motor_{ids}: Current mode is = {[info[mode] if mode is not None else None for mode in modes]}")

        return modes
    
    def get_voltage(self, ids:list[int]=None):
        if ids is None: 
            ids = list(self.motors.keys())

        voltages = [self.motors[id].get_voltage() for id in ids]
        if voltages and self.GIVE_INFO:
            print(f"[#]: Motor_{ids}: Current voltage is = {voltages} V")

        return voltages
    
    def get_load(self, ids:list[int]=None):
        if ids is None: 
            ids = list(self.motors.keys())

        loads = [self.motors[id].get_load() for id in ids]
        if loads and self.GIVE_INFO:
            print(f"[#]: Motor_{ids}: Current load is = {loads} %")

        return loads

    def get_motor_position(self, ids:list[int]=None):
        if ids is None: 
            ids = list(self.motors.keys())

        # if len(ids) > 3:
        #     return self.get_sync_motor_position()

        positions = [self.motors[id].get_motor_position() for id in ids]
        if positions and self.GIVE_INFO:
            print(f"[#]: Motor_{ids}: Current position is = {positions}º")

        return positions
    
    def get_velocity_limit(self, ids:list[int]=None):
        if ids is None: 
            ids = list(self.motors.keys())

        positions = [self.motors[id].get_velocity_limit() for id in ids]
        if positions and self.GIVE_INFO:
            print(f"[#]: Motor_{ids}: Current velocity limit is = {positions} / 1023")

        return positions

    def config_sync_read(self):
        # Initialize GroupSyncRead instace for Present Position
        self.groupSyncRead = GroupSyncRead(self.portHandler, self.packetHandler, Motor.ADDR_MX_PRESENT_POSITION, 4)

        # Add parameter storage for Dynamixel#1 present position value
        for motor_id in self.motors:
            if not self.groupSyncRead.addParam(motor_id) :
                print(f"[ID:{motor_id}] groupSyncRead addparam failed")
                return f"[ID:{motor_id}] groupSyncRead addparam failed"
            
        return f"[i]: GroupSyncRead added motor {list(self.motors.keys())}"
            
    def get_sync_motor_position(self):
        for _ in range(5):
            dxl_comm_result = self.groupSyncRead.txRxPacket()

            if dxl_comm_result == COMM_SUCCESS:
                dxl_getdata_results = [self.groupSyncRead.isAvailable(motor_id, Motor.ADDR_MX_PRESENT_POSITION, 4) for motor_id in self.motors]
                if not False in dxl_getdata_results:
                    break
                else:
                    error_msg = f"[!]: GroupSyncRead getdata failed: {dxl_getdata_results}"
            else:
                error_msg = f"[!]: {self.packetHandler.getTxRxResult(dxl_comm_result)}"
        else:
            print(error_msg)
            return error_msg
        

        position = [self.groupSyncRead.getData(motor_id, Motor.ADDR_MX_PRESENT_POSITION, 4) for motor_id in self.motors]

        MAX_GOAL                    = 1048575           # Maximum goal input. (4095 == 360º).
        MAX_REVOLUTIONS             = MAX_GOAL/4095     # Maximum number of revolutions of the motor (256).

        pos = list(round(interp(position, [-MAX_GOAL, MAX_GOAL], [-MAX_REVOLUTIONS*360,MAX_REVOLUTIONS*360]), 2))
        
        if self.GIVE_INFO:
            print(f"[#]: Motor_{list(self.motors.keys())}: Current position is = {pos}º")

        return pos

    def set_motor_position(self, goal:int, ids:list[int]=None):
        if ids is None: 
            ids = self.motors

        succeded = [id for id in ids if self.motors[id].set_motor_position(goal)]
        if succeded and self.GIVE_INFO:
            print(f"[#]: Motor_{succeded}: Goal position has been set = [{goal}º]")
        return succeded

    def set_motor_velocity(self, goal:int, ids:list[int]=None):
        "goal: int-> -229 ~ 229"

        if ids is None: 
            ids = self.motors

        succeded = [id for id in ids if self.motors[id].set_motor_velocity(goal)]
        if succeded and self.GIVE_INFO:
            print(f"[#]: Motor_{succeded}: Goal velocity has been set = [{goal}]")
        return succeded

    def set_motor_pwm(self, goal:int, ids:list[int]=None):
        "goal: int -> 0-100% pwm"
        if ids is None: 
            ids = self.motors

        succeded = [id for id in ids if self.motors[id].set_motor_pwm(goal)]
        if succeded and self.GIVE_INFO:
            print(f"[#]: Motor_{succeded}: Goal PWM has been set = [{goal}]")
        return succeded

    def set_motor_baudrate(self, baud:int, ids:list[int]=None):
        if ids is None: 
            ids = self.motors

        succeded = [id for id in ids if self.motors[id].set_motor_baudrate(baud)]

        self.begin(baud=baud)
        self.find_motors(self.n_motors)

        if succeded and self.GIVE_INFO:
            print(f"[#]: Motor_{succeded}: Baudrate has been set = [{baud}]")
        return succeded

    def get_motor_baudrate(self, ids:list[int]=None):
        if ids is None: 
            ids = list(self.motors.keys())

        baudrate = [self.motors[id].get_motor_baudrate() for id in ids]
        if baudrate and self.GIVE_INFO:
            print(f"[#]: Motor_{ids}: Current baudrate is = {baudrate}")

        return baudrate

    def __del__(self):
        if self.portHandler is not None:
            self.motors.clear()

            if self.portHandler.is_open:
                self.portHandler.closePort()


if __name__ == "__main__":

    controller = Controller()

    # controller.config_sync_read()

    
    # controller.get_motor_position()
    

    controller.get_voltage()

    # # controller.set_led(1, [2])
    # controller.get_motor_position()


    # # controller.set_torque(0)
    # # controller.set_mode(0)
    # controller.set_torque(1, [2])
    
    # # time.sleep(1)
    # controller.set_motor_position(0, [2])
    # time.sleep(3)
    # controller.get_motor_position()
    # print()

    # # controller.set_motor_position(360,[2])
    # # time.sleep(3)
    # # controller.get_motor_position()
    # # # controller.set_motor_position(0)
    # # # time.sleep(3)
    # # print()

    # controller.set_torque(0)
    # controller.set_mode(1)
    # controller.get_mode()
    # controller.set_torque(1)

    # time.sleep(1)
    # print()

    # controller.set_motor_velocity(50)

    # time.sleep(3)
    # print()
    
    # controller.set_motor_velocity(0)

    # time.sleep(1)
    # print()

    # controller.get_motor_position()
    # controller.set_torque(0)
    # controller.set_led(0)

