import numpy as np
import sys, cv2, time
from client import Client
from itertools import cycle

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *



class MainWindow(QMainWindow):
    command_signal = pyqtSignal(str)

    L_AND_R = 1
    MIDDLE = 2
    INDEX = 3
    THUMB = 4
    HINCH = 0

    style = """
        QMainWindow {
            background-color: rgb(40,40,40);
        }

        QLabel#menuBar_button {
            background-color: rgb(40,40,40);
            color: white;
            padding: 10px;
            padding-top: 2px;
            padding-bottom: 5px;
        }
        QLabel#menuBar_button:hover {
            background-color: rgb(60,60,60);
            border-radius: 6px;
        }
        QLabel[mode="clicked"] {
            background-color: rgb(40,40,40);
        }

        QLabel#menuBar_button_enabled {
            color: white;
            padding: 10px;
            padding-top: 2px;
            padding-bottom: 5px;
            background-color: rgb(38,79,120);     /*rgb(236, 74, 74*/
        }



        QMenu {
            background-color: rgb(40,40,40);
            color: white;
            border: 1px solid black;
            padding: 4px;
        }

        QMenu::item {
            border-radius: 6px;
            border-style: outset;
            padding: 4px;
            padding-right: 20px;
        }

        QMenu::item::selected {
            background-color: rgb(60,60,60);
        }


        QPushButton {
            background-color: rgb(40,40,40);
            color: rgb(255,255,255);
            border: 1px solid black;

            border-radius: 3px;
            border-style: outset;
            padding: 10px;
        }
        QPushButton:hover {
            background-color: rgb(60,60,60);
        }
        QPushButton:pressed {
            background-color: rgb(50,50,50);
        }


        QLabel {
            color: rgb(255,255,255);
        }

        QLabel#config {
            padding: 4px;
            padding-left: 6px;
        }

        QLabel#config:hover {
            background-color: rgb(60,60,60);
            border-radius: 6px;
            border-style: outset;
        }

        QFrame#menuBar_line {
            background-color: rgb(60,60,60);
        }

        QLineEdit {
            background-color: rgb(50,50,50);
            color: white;
            padding: 3px;
            border: 1px solid #000;
            border-radius: 3px;
            border-style: outset;
        }
        QLineEdit:focus {
            border: 1px solid rgb(0, 153, 188);
        }


        QWidget {
            background-color: rgb(40,40,40);
        }
        QComboBox, QAbstractItemView {
            padding: 3px;
            border: 1px solid #000;
            border-radius: 3px;
            border-style: outset;
            color: white;
            min-width: 3em;

            background-color: rgb(50,50,50);
            selection-background-color: rgb(40,40,40);
        }
        """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prosthetic hand - GUI")

        self.label_to_modify = None
        self.prev_time = 0
        self.show_fps = False
        self.show_recording = False
        self.saved_config = {}
        self.cameras = {}
        self.set_open_position = True
        self.set_close_position = False
        self.done = False

        # Layoutsl
        vlayout = QVBoxLayout()
        menu_layout = QHBoxLayout()

        main_layout = QHBoxLayout()
        right_layout = QHBoxLayout()

        # Establecer márgenes a cero para eliminar la separación
        menu_layout.setAlignment(Qt.AlignLeft)

        menu_layout.setContentsMargins(0, 0, 0, 0)
        vlayout.setContentsMargins(0,5, 0, 5)
        menu_layout.setSpacing(0)

        # Setup menubar.
        self.setup_menubar(menu_layout)


        # Setup main content.

        backg_img = np.zeros([1080,1240,3],dtype=np.uint8)
        self.backg_img = QImage(backg_img, backg_img.shape[1], backg_img.shape[0], QImage.Format_RGB888).rgbSwapped()

        self.zero_thread = Zero_Thread()
        self.zero_thread.DataUpdate.connect(self.update_data) # If a signal with a frame is received, update image.
        self.zero_thread.finished.connect(self.stopped_video)
        self.command_signal.connect(self.zero_thread.set_command)


        self.image = QLabel(self)
        scaled_img = self.backg_img.scaled(int(self.backg_img.width()*0.55), int(self.backg_img.height()*0.55), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image.setPixmap(QPixmap(scaled_img))
        self.image.resizeEvent = self.resize_image
        self.image.setBaseSize(int(self.backg_img.width()*0.2),int(self.backg_img.height()*0.2))
        self.image.setMinimumSize(int(self.backg_img.width()*0.1),int(self.backg_img.height()*0.1))
        main_layout.addWidget(self.image)
        main_layout.setStretchFactor(self.image, 1)


        # Right layout:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding))
        widget = QWidget(self)
        scroll.setWidget(widget)
        hbox = QHBoxLayout()
        widget.setLayout(hbox)



        vbox = self.setup_scroll()
        hbox.addLayout(vbox)
        vbox = self.setup_right_pregrasps()
        hbox.addLayout(vbox)




        # right_pregrasps = self.setup_right_pregrasps(scroll)


        right_layout.addWidget(scroll)
        # right_layout.addLayout(right_pregrasps)

        main_layout.addLayout(right_layout)
        main_layout.addLayout(right_layout)
        main_layout.setContentsMargins(5,0,0,5)

        vlayout.addLayout(menu_layout)
        vlayout.addLayout(main_layout)


        widget = QWidget()
        widget.setMouseTracking(True)
        widget.setLayout(vlayout)
        self.setCentralWidget(widget)

        self.setStyleSheet(self.style)

    def resize_image(self,event):
        if not self.zero_thread.ThreadActive:
            self.set_background_img()

        # Call the base class resizeEvent
        QLabel.resizeEvent(self.image, event)

    def update_data(self, msg, image):
        load = []
        for id, motor in enumerate(self.zero_thread.motors):
            self.labels[id].setText(motor["position"])

            if motor["torque"] and "mode" in motor.keys():
                if motor["mode"] == 0: # Position mode.
                    mode = "pos"
                elif motor["mode"] == 1: # Velocity mode.
                    mode = "vel"
                elif motor["mode"] == 3: # PWM mode.
                    mode = "pwm"
                else:
                    mode = "off"
            else:
                mode = "off"

            self.btns[id].setProperty("mode", mode)
            self.btns[id+5].setProperty("mode", mode)

            self.btns[id].setStyleSheet(self.btns[id].styleSheet())
            self.btns[id+5].setStyleSheet(self.btns[id+5].styleSheet())

            if self.set_open_position:
                slider = self.sliders[id]
                zero = round(float(motor["position"]))

                if id == 1:
                    slider.setMaximum(zero)
                    slider.setValue(zero)
                else:
                    slider.setMinimum(zero)
                    slider.setValue(zero)

            if self.set_close_position:
                slider = self.sliders[id]
                closed_pos = round(float(motor["position"]))

                if id == 1:
                    slider.setMinimum(closed_pos)

                else:
                    slider.setMaximum(closed_pos)

            load.append(motor["load"])


        self.set_open_position = False
        self.set_close_position = False

        if self.zero_thread.do_detection:
            print(f"{msg} - detection: {self.zero_thread.color_percentage*100:.2f} %")

            if self.zero_thread.color_percentage >= 0.10 and self.done == False:
                pos = self.sliders[2].minimum() + 60
                self.done = True
                self.command_signal.emit(f"set_motor_position({pos}, [{2}])")
            elif self.zero_thread.color_percentage < 0.10 and self.done == True:
                print(len(self.zero_thread.command))
                pos = self.sliders[2].minimum()
                self.done = False
                self.command_signal.emit(f"set_motor_position({pos}, [{2}])")

        else:
            print(msg)
            # print(self.zero_thread.motors)

        self.update_frame(image)

    def update_frame(self, cv2_img):
        if self.show_fps:
            cv2_img = self.print_fps(cv2_img)

        image = QImage(cv2_img.data, cv2_img.shape[1], cv2_img.shape[0], QImage.Format_RGB888).rgbSwapped()
        self.image.setPixmap(QPixmap(image).scaled(self.image.width(), self.image.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def set_background_img(self):
        img = QPixmap(self.backg_img)
        scaled_img = img.scaled(self.image.width(), self.image.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image.setPixmap(scaled_img)

    def print_fps(self, img):
        elapsed_time = time.time() - self.prev_time

        if elapsed_time != 0:
            fps = round(1/elapsed_time, 2)
            self.prev_time = time.time()
            cv2.putText(img, str(fps), (7, 25), cv2.FONT_HERSHEY_SIMPLEX , 0.75, (100, 255, 0), 1, cv2.LINE_AA)

        return img

    def start_video(self, mode):

        if mode == "Play":
            if not self.zero_thread.isRunning() and not self.zero_thread.ThreadActive:
                self.zero_thread.start()

        elif mode == "Stop" and self.zero_thread.isRunning():
                self.zero_thread.stop()

    def stopped_video(self):
        self.set_background_img()

    def setup_scroll(self):
        vbox = QVBoxLayout()

        self.btns       = []
        self.sliders    = []
        self.edits      = []
        self.labels     = []

        vbox.addWidget(QLabel("- Position Control"))

        for id in range(5):
            options_layout = QHBoxLayout()
            options_layout.setContentsMargins(0,10,0,10)

            btn = QPushButton(objectName="show_lines_btn")
            btn.setFixedSize(15, 15)
            btn.setProperty("id", id)
            btn.setProperty("mode", "off")
            btn.setStyleSheet("QPushButton {background-color: #FF0000; padding: 0px;}"
                            + "QPushButton:hover {background-color: #646464;}"
                            + "QPushButton[mode='pos'] {background-color: #00FF00}")

            btn.pressed.connect(self.torque_btn_pressed)


            motor_name_label = QLabel(f"Motor {id}:", self)

            slider = QSlider(self)
            slider.setProperty("id", id)
            slider.setMinimum(-200)
            slider.setMaximum(600)
            slider.setValue(0)
            slider.setOrientation(Qt.Horizontal)  # Vertical slider
            slider.setTickInterval(1)
            slider.valueChanged.connect(self.slider_changed)

            edit = QLineEdit(self)
            edit.setProperty("id", id)
            edit.setText('0')
            edit.setFixedWidth(30)  # Adjust the width here
            edit.returnPressed.connect(self.slider_text_changed)

            label = QLabel('0')
            label.setProperty("id", id)
            label.setFixedWidth(40)
            label.setAlignment(Qt.AlignCenter)


            options_layout.addWidget(btn)
            options_layout.addWidget(motor_name_label)
            options_layout.addWidget(slider)
            options_layout.addWidget(edit)
            options_layout.addWidget(label)

            self.btns.append(btn)
            self.sliders.append(slider)
            self.edits.append(edit)
            self.labels.append(label)

            # vbox.insertLayout(len(vbox.children()), options_layout)
            vbox.addLayout(options_layout)

        vbox.addSpacing(20)
        vbox.addWidget(QLabel("- Speed Control"))

        for id in range(5,10):
            options_layout = QHBoxLayout()
            options_layout.setContentsMargins(0,10,0,10)

            btn = QPushButton(objectName="show_lines_btn")
            btn.setFixedSize(15, 15)
            btn.setProperty("id", id)
            btn.setProperty("mode", "off")
            btn.setStyleSheet("QPushButton {background-color: #FF0000; padding: 0px;}"
                            + "QPushButton:hover {background-color: #646464;}"
                            + "QPushButton[mode='vel'] {background-color: #00FF00}")

            btn.pressed.connect(self.torque_btn_pressed)


            motor_name_label = QLabel(f"Motor {id-5}:", self)

            slider = QSlider(self)
            slider.setProperty("id", id)
            slider.setMinimum(-229)
            slider.setMaximum(229)
            slider.setValue(0)
            slider.setOrientation(Qt.Horizontal)  # Vertical slider
            slider.setTickInterval(1)
            slider.valueChanged.connect(self.slider_changed)

            edit = QLineEdit(self)
            edit.setProperty("id", id)
            edit.setText('0')
            edit.setFixedWidth(30)  # Adjust the width here
            edit.returnPressed.connect(self.slider_text_changed)

            label = QLabel('0')
            label.setProperty("id", id)
            label.setFixedWidth(40)
            label.setAlignment(Qt.AlignCenter)


            options_layout.addWidget(btn)
            options_layout.addWidget(motor_name_label)
            options_layout.addWidget(slider)
            options_layout.addWidget(edit)
            options_layout.addWidget(label)

            self.btns.append(btn)
            self.sliders.append(slider)
            self.edits.append(edit)
            self.labels.append(label)

            # vbox.insertLayout(len(vbox.children()), options_layout)
            vbox.addLayout(options_layout)


        return vbox

    def setup_right_pregrasps(self):
        vbox = QVBoxLayout()

        # First row
        options_layout = QHBoxLayout()
        options_layout.setContentsMargins(0,10,0,10)

        btn = QPushButton(text="Power Grasp", objectName="show_lines_btn")
        btn.pressed.connect(self.do_pregrasp)
        options_layout.addWidget(btn)

        btn = QPushButton(text="Tripode Grasp", objectName="show_lines_btn")
        btn.pressed.connect(self.do_pregrasp)
        options_layout.addWidget(btn)
        vbox.addLayout(options_layout)


        # Second row
        options_layout = QHBoxLayout()
        options_layout.setContentsMargins(0,10,0,10)

        btn = QPushButton(text="Pinch Grasp", objectName="show_lines_btn")
        btn.pressed.connect(self.do_pregrasp)
        options_layout.addWidget(btn)

        btn = QPushButton(text="Lateral pinch Grasp", objectName="show_lines_btn")
        btn.pressed.connect(self.do_pregrasp)
        options_layout.addWidget(btn)
        vbox.addLayout(options_layout)

        # Third row
        options_layout = QHBoxLayout()
        options_layout.setContentsMargins(0,10,0,10)

        btn = QPushButton(text="Open Fingers", objectName="show_lines_btn")
        btn.pressed.connect(self.do_pregrasp)
        options_layout.addWidget(btn)

        btn = QPushButton(text="Close Fingers", objectName="show_lines_btn")
        btn.pressed.connect(self.do_pregrasp)
        options_layout.addWidget(btn)
        vbox.addLayout(options_layout)

        # Forth row
        options_layout = QHBoxLayout()
        options_layout.setContentsMargins(0,10,0,10)

        btn = QPushButton(text="Start Torque", objectName="show_lines_btn")
        btn.pressed.connect(self.do_pregrasp)
        options_layout.addWidget(btn)

        btn = QPushButton(text="Stop Torque", objectName="show_lines_btn")
        btn.pressed.connect(self.do_pregrasp)
        options_layout.addWidget(btn)
        vbox.addLayout(options_layout)


        return vbox

    def do_pregrasp(self):
        btn = self.sender()

        if btn.text() == "Power Grasp":
            self.command_signal.emit(f"set_torque(0)")
            self.command_signal.emit(f"set_mode(2)")
            self.command_signal.emit(f"set_torque(1)")

            # Close hinch
            self.command_signal.emit(f"set_motor_pwm(35, {[self.HINCH]})")
            self.command_signal.emit(f"set_motor_pwm(20, {[self.THUMB]})")

            # close other fingers
            self.command_signal.emit(f"set_motor_pwm(-40, {[self.L_AND_R]})")
            self.command_signal.emit(f"set_motor_pwm(20, {[self.MIDDLE]})")
            self.command_signal.emit(f"set_motor_pwm(20, {[self.INDEX]})")

            # Close thumb:
            # time.sleep(2)

        elif btn.text() == "Tripode Grasp":
            self.command_signal.emit(f"set_torque(0)")
            self.command_signal.emit(f"set_mode(2)")
            self.command_signal.emit(f"set_torque(1)")

            # Close hinch
            self.command_signal.emit(f"set_motor_pwm(30, {[self.HINCH]})")

            # close other fingers
            self.command_signal.emit(f"set_motor_pwm(30, {[self.MIDDLE]})")
            self.command_signal.emit(f"set_motor_pwm(30, {[self.INDEX]})")
            
            # Close thumb
            time.sleep(2)
            self.command_signal.emit(f"set_motor_pwm(20, {[self.THUMB]})")

        elif btn.text() == "Pinch Grasp":
            self.command_signal.emit(f"set_torque(0)")
            self.command_signal.emit(f"set_mode(2)")
            self.command_signal.emit(f"set_torque(1)")

            # Close hinch
            self.command_signal.emit(f"set_motor_pwm(30, {[self.HINCH]})")

            # close other fingers
            self.command_signal.emit(f"set_motor_pwm(30, {[self.INDEX]})")
            
            # Close thumb
            time.sleep(2)
            self.command_signal.emit(f"set_motor_pwm(20, {[self.THUMB]})")

        elif btn.text() == "Lateral pinch Grasp": ...

        elif btn.text() == "Open Fingers":
            self.command_signal.emit(f"set_torque(0, {[self.L_AND_R, self.MIDDLE, self.INDEX, self.THUMB, self.HINCH]})")
            self.command_signal.emit(f"set_mode(0, {[self.L_AND_R, self.MIDDLE, self.INDEX, self.THUMB, self.HINCH]})")
            self.command_signal.emit(f"set_torque(1, {[self.L_AND_R, self.MIDDLE, self.INDEX, self.THUMB, self.HINCH]})")

            self.command_signal.emit(f"set_motor_position({self.sliders[1].maximum()}, {[self.L_AND_R]})")
            self.command_signal.emit(f"set_motor_position({self.sliders[2].minimum()}, {[self.MIDDLE]})")
            self.command_signal.emit(f"set_motor_position({self.sliders[3].minimum()}, {[self.INDEX]})")
            self.command_signal.emit(f"set_motor_position({self.sliders[4].minimum()}, {[self.THUMB]})")
            self.command_signal.emit(f"set_motor_position({self.sliders[0].minimum()}, {[self.HINCH]})")

        elif btn.text() == "Close Fingers":
            self.command_signal.emit(f"set_torque(0, {[self.L_AND_R, self.MIDDLE, self.INDEX]})")
            self.command_signal.emit(f"set_mode(2, {[self.L_AND_R, self.MIDDLE, self.INDEX]})")
            self.command_signal.emit(f"set_torque(1, {[self.L_AND_R, self.MIDDLE, self.INDEX]})")

            self.command_signal.emit(f"set_motor_pwm(-40, {[self.L_AND_R]})")
            self.command_signal.emit(f"set_motor_pwm(30, {[self.MIDDLE]})")
            self.command_signal.emit(f"set_motor_pwm(40, {[self.INDEX]})")

        elif btn.text() == "Start Torque":
            self.command_signal.emit(f"set_torque(1)")
        
        elif btn.text() == "Stop Torque":
            self.command_signal.emit(f"set_torque(0)")
            
    def slider_changed(self, value):
        slider = self.sender()
        id = slider.property("id")

        self.edits[id].setText(str(value))
        if id < 5:
            self.command_signal.emit(f"set_motor_position({value}, [{id}])")
        else:
            self.command_signal.emit(f"set_motor_velocity({value}, [{id-5}])")

    def slider_text_changed(self):
        edit = self.sender()
        id = edit.property("id")

        try:
            value = int(edit.text())
            if self.sliders[id].minimum() <= value <= self.sliders[id].maximum():
                self.sliders[id].setValue(value)
            else:
                edit.setText(str(self.sliders[id].value()))
        except ValueError:
            edit.setText(str(self.sliders[id].value()))

    def torque_btn_pressed(self):
        btn = self.sender()
        id = btn.property("id")
        print(id)
        motor_id = id if id < 5 else id -5
        btn_pos = id < 5
        mode = btn.property("mode")

        if mode == "off": # Enable torque!.
            self.command_signal.emit(f"set_torque(1, [{motor_id}])")

        elif btn_pos and mode == "pos" or not btn_pos and mode == "vel": # Disable torque.
            self.command_signal.emit(f"set_torque(0, [{motor_id}])")

        elif btn_pos and mode == "vel" or not btn_pos and mode == "pos": # Switch velocity/position mode:
            self.command_signal.emit(f"set_torque(0, [{motor_id}])")
            self.command_signal.emit(f"set_mode({int(not btn_pos)}, [{motor_id}])")
            self.command_signal.emit(f"set_torque(1, [{motor_id}])")

    def setup_menubar(self, menu_layout):

        # Options for the Settings menu:
        settingsMenu = QMenu(self)
        settingsLabel = QLabel('Settings', self, objectName="menuBar_button")
        settingsLabel.mousePressEvent = lambda _: self.show_menu(settingsMenu, settingsLabel)

        self.settings_fps       = QAction(" Show FPS", settingsMenu, triggered=self.settings_actions, checkable=True)
        settingsMenu.addActions([self.settings_fps])

        menu_layout.addWidget(settingsLabel)

        # Options for the Camera menu:
        self.playLabel = QLabel('Start', self, objectName="menuBar_button")
        self.playLabel.mousePressEvent          = lambda _, mode="Play": self.start_video(mode)
        menu_layout.addWidget(self.playLabel)

        # Options for Pause button:
        self.stopLabel = QLabel('Stop', self, objectName="menuBar_button")
        self.stopLabel.mousePressEvent          = lambda _, mode="Stop": self.start_video(mode)
        menu_layout.addWidget(self.stopLabel)

        # Option for setting the extended position of the hand:
        self.openLabel = QLabel('Reset open position', self, objectName="menuBar_button")
        self.openLabel.mousePressEvent = lambda _: self.reset_opened_position()
        menu_layout.addWidget(self.openLabel)

        # Option for setting the closed position of the hand:
        self.closeLabel = QLabel('Reset close position', self, objectName="menuBar_button")
        self.closeLabel.mousePressEvent = lambda _: self.reset_closed_position()
        menu_layout.addWidget(self.closeLabel)

        # Option for toggle the color detection:
        self.colorLabel = QLabel('Color detection', self, objectName="menuBar_button")
        self.colorLabel.mousePressEvent = lambda _: self.toggle_color_detection()
        menu_layout.addWidget(self.colorLabel)

    def settings_actions(self):
        button = self.sender()
        parent = self.sender().parent()

        if button.text() == self.settings_fps.text():
            self.show_fps = not self.show_fps

    def show_menu(self, menu, label):

        menu.aboutToHide.connect(lambda: label.setStyleSheet(""))

        # Obtener la posición global del QLabel

        label_pos = label.mapToGlobal(QPoint(0, 0))

        # Mostrar el menú debajo del QLabel
        menu_pos = QPoint(label_pos.x(), label_pos.y() + label.height())
        menu.exec_(menu_pos)

    def menuLabel_release(self, button):
        button.setStyleSheet(self.style)

    def reset_opened_position(self):
        self.set_open_position = True

    def reset_closed_position(self):
        self.set_close_position = True

    def toggle_color_detection(self):
        self.zero_thread.do_detection = not self.zero_thread.do_detection

    def closeEvent(self, event):
        self.zero_thread.stop()
        event.accept()



class Zero_Thread(QThread, Client):
    DataUpdate = pyqtSignal(str, np.ndarray)

    def __init__(self):
        super().__init__()
        self.ThreadActive = False
        self.command = []
        self.motors = [{"position": '0', "torque": 0, "mode": 0, "load": 0} for _ in range(5)]
        # self.ctrl_func = cycle([self.update_motor_positions, self.update_motor_torques, self.update_motor_loads, self.update_motor_modes])
        self.ctrl_func = cycle([self.update_motor_positions, self.update_motor_loads, self.update_motor_torques, self.update_motor_loads, self.update_motor_modes, self.update_motor_loads])
        self.color_percentage = 0
        self.do_detection = False

    def run(self):
        self.ThreadActive = True
        timer = 0

        while self.ThreadActive:

            if time.time() - timer >=0.25:
                next(self.ctrl_func)()
                timer = time.time()
            else:
                start = time.time()

                if self.command:
                    command = self.command.pop(0)
                else:
                    command = ""

                msg, img = self.do_command(command)

                elapsed = time.time() - start

                msg = f"Received message: {msg} (elapsed: {elapsed:.3f} s.)"

                self.DataUpdate.emit(msg, img)

        self.stop()

    def stop(self):
        self.ThreadActive = False
        self.quit()

    def do_command(self, command = ""):
        self.send_msg(command)
        msg, img_bgr = self.get_jpg()

        if self.do_detection:
            img_bgr = self.detect_color(img_bgr)

        return  msg, img_bgr

    def set_command(self, command:str):
        if len(self.command) > 10:
            self.command[-1] = command
        else:
            self.command.append(command)

    def update_motor_positions(self):
        msg, img = self.do_command("get_motor_position()")

        str_positions = msg[1:msg.index("]")]
        positions = str_positions.split(",")

        for i, pos in enumerate(positions):
            self.motors[i]["position"] = pos

        self.DataUpdate.emit(msg,img)

    def update_motor_torques(self):
        msg, img = self.do_command("get_torque()")

        str_torques = msg[1:msg.index("]")]
        torques = str_torques.split(",")

        for i, torque in enumerate(torques):
            self.motors[i]["torque"] = int(torque)

        self.DataUpdate.emit(msg,img)

    def update_motor_loads(self):
        msg, img = self.do_command("get_load()")

        str_loads = msg[1:msg.index("]")]
        loads = str_loads.split(",")

        for i, load in enumerate(loads):
            self.motors[i]["load"] = float(load)

        self.DataUpdate.emit(msg,img)

    def update_motor_modes(self):
        msg, img = self.do_command("get_mode()")

        str_modes = msg[1:msg.index("]")]
        modes = str_modes.split(",")

        for i, mode in enumerate(modes):
            self.motors[i]["mode"] = int(mode)


        self.DataUpdate.emit(msg, img)

    def detect_color(self, img):
        # Convert the image from BGR to HSV color space
        hsv_image = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Create a mask using the specified HSV range
        mask = cv2.inRange(hsv_image, np.array([80, 50, 20]), np.array([130, 255, 255]))

        # Calculate the percentage of the mask area relative to the total image area
        mask_area = cv2.countNonZero(mask)
        total_area = img.shape[0] * img.shape[1]
        self.color_percentage = mask_area / total_area

        result = cv2.bitwise_and(img, img, mask=mask)

        return result

if __name__ == "__main__":

    app = QApplication(sys.argv + ['-platform', 'windows:darkmode=1'])

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

