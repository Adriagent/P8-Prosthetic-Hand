from numpy import interp
from typing import Union

from dynamixel_sdk import PortHandler, COMM_SUCCESS 
from packet_handler_modified_p_2 import Protocol2PacketHandler as Protocol_Handler



class MX_28R:
    # Control table address
    ADDR_MX_TORQUE_ENABLE       = 64                # Control address for toggling torque. + 1 byte, 1 byte
    ADDR_MX_PRESENT_POSITION    = 132               # Control address for getting current position.
    ADDR_MX_LED                 = 65                # Control address for toggling motor LED. 
    ADDR_MX_MODE                = 11                # Control address for switching operating modes. (2.0)
    ADDR_MX_GOAL_POS            = 116               # Control address for setting a goal position.
    ADDR_MX_GOAL_PWM            = 100               # Control address for setting a goal pwm.
    ADDR_MX_GOAL_VEL            = 104               # Control address for setting a goal pwm.
    ADDR_MX_BAUDRATE            = 8                 # Control address for setting a baudrate.
    ADDR_MX_VOLTAGE_INPUT       = 144               # Control address for setting a voltage input.
    ADDR_MX_PRESENT_LOAD        = 126               # Control address for setting a present load.

    # Operating modes
    MODE_POSITION               = 4                 # Operating mode setting for enabling the Position mode.
    MODE_VELOCITY               = 1
    MODE_PWM                    = 16                # Operating mode setting for enabling the PWM mode.

    # Baudrate modes:
    BAUD_57600                  = 1                 # Value for setting the baudrate to 57_600.
    BAUD_115200                 = 2                 # Value for setting the baudrate to 115_200.
    BAUD_1M                     = 3                 # Value for setting the baudrate to 1M.

    # Goal positions
    MAX_GOAL                    = 1048575           # Maximum goal input. (4095 == 360º).
    MAX_REVOLUTIONS             = MAX_GOAL/4095     # Maximum number of revolutions of the motor (256). 
    MAX_PWM                     = 885    
    MAX_VEL                     = 1023              # Maximum speed [0-1023] (0-229rpm)
    MAX_RPM                     = 229

    def __init__(self, _portHandler:PortHandler, _packetHandler:Protocol_Handler, _id:int):
        self.portHandler    = _portHandler
        self.packetHandler  = _packetHandler
        self.id             = _id

    def debug_msg(self, dxl_comm_result, dxl_error, addr):
        if dxl_comm_result != COMM_SUCCESS:
            print(f"[!]: (ID_{self.id} - ADDR_{addr})  {self.packetHandler.getTxRxResult(dxl_comm_result)}")
        elif dxl_error != 0:
            print(f"[!]: (ID_{self.id} - ADDR_{addr})  {self.packetHandler.getRxPacketError(dxl_error)}")
        else:
            return True
        
        return False

    def safe_command(self, fn, *arg) -> Union[bool,tuple[bool,int]]:
        for _ in range(5):
            *output, dxl_comm_result, dxl_error = fn(*arg)

            if dxl_comm_result == COMM_SUCCESS and dxl_error == 0:
                return (True, *output) if output else True
        else:
            self.debug_msg(dxl_comm_result, dxl_error, arg[2])

        return (False, *output) if output else False

    def is_torque_enabled(self):
        dxl_torque_enabled, _, _ = self.packetHandler.read1ByteTxRx(self.portHandler, self.id, self.ADDR_MX_TORQUE_ENABLE)
        return dxl_torque_enabled

    def set_led(self, mode) -> bool:
        return self.safe_command(self.packetHandler.write1ByteTxRx, self.portHandler, self.id, self.ADDR_MX_LED, mode)

    def set_torque(self, mode)-> bool:
        return self.safe_command(self.packetHandler.write1ByteTxRx, self.portHandler, self.id, self.ADDR_MX_TORQUE_ENABLE, mode)

    def get_torque(self):
        result, dxl_torque = self.safe_command(self.packetHandler.read1ByteTxRx, self.portHandler, self.id, self.ADDR_MX_TORQUE_ENABLE)
        return dxl_torque if result else None

    def set_mode(self, mode) -> bool:
        "mode: int -> 0: Position, 1: Velocity, 2: PWM"

        selected = [self.MODE_POSITION, self.MODE_VELOCITY, self.MODE_PWM][mode] # 4 for Multi-turn | 16 for PWM
        return self.safe_command(self.packetHandler.write1ByteTxRx, self.portHandler, self.id, self.ADDR_MX_MODE, selected)
    
    def get_mode(self):
        result, dxl_mode = self.safe_command(self.packetHandler.read1ByteTxRx, self.portHandler, self.id, self.ADDR_MX_MODE)
        mode = [self.MODE_POSITION, self.MODE_VELOCITY, self.MODE_PWM].index(dxl_mode)

        return mode if result else None
    
    def get_voltage(self):
        result, dxl_volt = self.safe_command(self.packetHandler.read2ByteTxRx, self.portHandler, self.id, self.ADDR_MX_VOLTAGE_INPUT)
        return dxl_volt/10 if result else None
    
    def get_load(self):
        result, dxl_load = self.safe_command(self.packetHandler.read2ByteTxRx, self.portHandler, self.id, self.ADDR_MX_PRESENT_LOAD)
        if dxl_load > 1000:
            dxl_load = 65_535 - dxl_load

        return dxl_load/10 if result else None

    def get_motor_position(self):
        """
        Returns:
          result:   Boolean indicating whether or not it succeded getting the motor position.
          position: Current motor position in degrees.
        """
        result, position_scaled = self.safe_command(self.packetHandler.read2ByteTxRx, self.portHandler, self.id, self.ADDR_MX_PRESENT_POSITION)
        position = round(interp(position_scaled, [-self.MAX_GOAL, self.MAX_GOAL], [-self.MAX_REVOLUTIONS*360,self.MAX_REVOLUTIONS*360]),2)
        return position if result else None
    
    def get_velocity_limit(self):
        """
        Returns:
          result:   Boolean indicating whether or not it succeded getting the motor position.
          position: Current motor position in degrees.
        """
        result, position_scaled = self.safe_command(self.packetHandler.read4ByteTxRx, self.portHandler, self.id, 44)
        # position = interp(position_scaled, [-self.MAX_GOAL, self.MAX_GOAL], [-self.MAX_REVOLUTIONS*360,self.MAX_REVOLUTIONS*360])
        # position = round(position,2)
        return position_scaled if result else None

    def set_motor_position(self, goal) -> bool:
        goal_scaled = round(interp(goal, [-self.MAX_REVOLUTIONS*360,self.MAX_REVOLUTIONS*360], [-self.MAX_GOAL, self.MAX_GOAL]))
        return self.safe_command(self.packetHandler.write4ByteTxRx, self.portHandler, self.id, self.ADDR_MX_GOAL_POS, goal_scaled)

    def set_motor_velocity(self, goal) -> bool:
        goal_scaled = round(interp(goal, [-self.MAX_RPM,self.MAX_RPM], [-self.MAX_VEL, self.MAX_VEL]))
        return self.safe_command(self.packetHandler.write4ByteTxRx, self.portHandler, self.id, self.ADDR_MX_GOAL_VEL, goal_scaled)
    
    def set_motor_pwm(self, goal) -> bool:
        goal_scaled = round(goal/100*self.MAX_PWM)
        return self.safe_command(self.packetHandler.write2ByteTxRx, self.portHandler, self.id, self.ADDR_MX_GOAL_PWM, goal_scaled)

    def set_motor_baudrate(self, baud) -> bool:
        if baud == 57600:
            baud_mode = self.BAUD_57600
        elif baud == 115200:
            baud_mode = self.BAUD_115200
        elif baud == 1_000_000:
            baud_mode = self.BAUD_1M
        
        return self.safe_command(self.packetHandler.write1ByteTxRx, self.portHandler, self.id, self.ADDR_MX_BAUDRATE, baud_mode)

    def get_motor_baudrate(self):
        baudrate = -1
        result, baud_mode = self.safe_command(self.packetHandler.read1ByteTxRx, self.portHandler, self.id, self.ADDR_MX_BAUDRATE)

        if baud_mode == self.BAUD_57600:
            baudrate = 57600
        elif baud_mode == self.BAUD_115200:
            baudrate = 115200
        elif baud_mode == self.BAUD_1M:
            baudrate = 1_000_000

        return baudrate if result else None

    def __del__(self):
        if self.is_torque_enabled():
            self.set_torque(0)

