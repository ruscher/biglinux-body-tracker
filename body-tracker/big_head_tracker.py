import subprocess
import threading
import time
import os
import sys
import argparse
import configparser
import math
import numpy as np
import tkinter as tk
from tkinter import messagebox
from PIL import Image
from pynput.mouse import Button, Controller



# Used to found files after use pyinstaller
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Configuration Functions
def read_config(var_name=None, section_name='General', config_file='config.conf', default_value=None):
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, '.config', 'biglinux-body-tracker')
    config_path = os.path.join(config_dir, config_file)

    config = configparser.ConfigParser()
    config.read(config_path)

    if var_name is None:
        return dict(config[section_name])

    if not config.has_option(section_name, var_name):
        return default_value

    return config[section_name][var_name]

def write_config(var_name, var_value, section_name='General', config_file='config.conf'):
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, '.config', 'biglinux-body-tracker')
    config_path = os.path.join(config_dir, config_file)

    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

    config = configparser.ConfigParser()
    config.read(config_path)

    if not config.has_section(section_name):
        config.add_section(section_name)

    config[section_name][var_name] = var_value

    with open(config_path, 'w') as configfile:
        config.write(configfile)

# Argument Parsing
arg_info = {
    'view': {
        'type': int,
        'help': 'Show webcam image',
        'default': 0
    },
    'mouseDetectionMode': {
        'type': int,
        'help': 'Mouse detection mode 1 or 2 or 3 or 4',
        'default': 4
    },
    'startIsNeutral': {
        'type': bool,
        'help': 'Start position is neutral position True or False',
        'default': True
    },
    'enableLeftEye': {
        'type': bool,
        'help': 'Use left eye blink True or False',
        'default': True
    },
    'enableRightEye': {
        'type': bool,
        'help': 'Use right eye blink True or False',
        'default': True
    },
    'leftEyeBlinkFunction': {
        'type': str,
        'help': 'clickLeft or clickCenter or clickRight or drag or doubleClick or scrollV or scrollH',
        'default': 'clickLeft'
    },
    'enableKiss': {
        'type': bool,
        'help': 'Use kiss True or False',
        'default': True
    },
    'webcamid': {
        'type': int,
        'help': 'Webcam ID',
        'default': 0
    },
    'webcamx': {
        'type': int,
        'help': 'Webcam X resolution',
        'default': 1024
    },
    'webcamy': {
        'type': int,
        'help': 'Webcam Y resolution',
        'default': 768
    },
    'webcamToRGB': {
        'type': bool,
        'help': 'Some webcams need conversion to RGB',
        'default': False
    },
    'fps': {
        'type': int,
        'help': 'Frames per second',
        'default': 15
    },
    'plot': {
        'type': int,
        'help': 'Plot the face landmarks',
        'default': 0
    },
    'blinkToClick': {
        'type': int,
        'help': 'Blink to click',
        'default': 1
    },
    'minimalMouseMoveY': {
        'type': int,
        'help': 'Minimal mouse move Y',
        'default': 3
    },
    'minimalMouseMoveX': {
        'type': int,
        'help': 'Minimal mouse move X',
        'default': 3
    },
    'slowMouseMoveY': {
        'type': int,
        'help': 'Slow mouse move Y',
        'default': 9
    },
    'slowMouseMoveX': {
        'type': int,
        'help': 'Slow mouse move X',
        'default': 9
    },
    'mouseSpeedX': {
        'type': int,
        'help': 'Mouse speed X',
        'default': 40
    },
    'mouseSpeedY': {
        'type': int,
        'help': 'Mouse speed Y',
        'default': 40
    },
    'autoBrightness': {
        'type': bool,
        'help': 'Automatically adjust brightness',
        'default': True
    },
    'mouthScroll': {
        'type': int,
        'help': 'Enable mouth scrolling',
        'default': 0
    },
}

parser = argparse.ArgumentParser()

# Add arguments to the parser
for arg_name, arg_details in arg_info.items():
    parser.add_argument(f'--{arg_name}', type=str, help=arg_details['help'], default=str(arg_details['default']))

# Parse provided arguments
args = parser.parse_args()

# Store provided arguments in a list
provided_args = []
for arg in vars(args):
    if f"--{arg}" in sys.argv:
        provided_args.append(arg)

# Function to update arguments based on provided arguments and settings
def update_arg(args, arg_name, default_value, provided_args):
    conf_value = read_config(arg_name, section_name='General', default_value=None)

    # If the argument is not provided in the command line, use config or default
    if arg_name not in provided_args:
        if conf_value is not None:
            setattr(args, arg_name, conf_value)
    else:
        # If provided in command line, write to config
        write_config(arg_name, str(getattr(args, arg_name)))

    # Get the value of the argument
    arg_value = getattr(args, arg_name)

    # If the argument is a boolean, convert to boolean
    if default_value is bool:
        arg_value = arg_value.lower() in ['true', 't', 'yes', 'y', '1']
    else:
        # If the argument is not a boolean, convert to the desired type
        arg_value = default_value(arg_value)

    # Set the value of the argument
    setattr(args, arg_name, arg_value)

# Update arguments using the update_arg function
for arg_name, arg_details in arg_info.items():
    update_arg(args, arg_name, arg_details['type'], provided_args)

# Initialize variables based on arguments
if not args.enableLeftEye:
    leftEye = 1
    leftEyeOld = 1
    leftEyeMean = 1
    leftEyeNormalized = 1

if not args.enableRightEye:
    rightEye = 1
    rightEyeOld = 1
    rightEyeMean = 1
    rightEyeNormalized = 1

# Initialize other global variables
overLeftEye = 0
overRightEye = 0
action = ''
mousePointYabsOld = 0
mousePointXabsOld = 0
mousePointXApply = 0
mousePointYApply = 0
leftEyeBlinkOld = 0
leftEyeBlink = 0
rightEyeBlink = 0
irisDistance = 1
kiss = 1
confirmationTimeout = 0
eyesOpen = 5
waitFrames = 10
clicked = False
leftClickedConstant = False
scrollModeVertical = False
scrollModeHorizontal = False
changeLeftMove = False
leftMoved = 'no'
changeRightMove = False
rightMoved = 'no'
stopCursor = False
slowMove = 10
rightEyeBlinkOld = 0
leftEyeBlinkOld = 0
leftEyeMean = 0
rightEyeMean = 0
mouthCenterLeftOld = 0
mouthCenterRightOld = 0
tooltipWait = False
mouthCenterLeftOldLock = False
mouthCenterRightOldLock = False
leftClicked = False
rightClicked = False
standByClick = False
frameNumber = 0
mousePositionFrameX = 0
mousePositionFrameY = 0
maybeScreenLimitX = 0
maybeScreenLimitY = 0
clicktime = 0
zeroPointX = None
zeroPointY = None
zeroPointX2 = None
zeroPointY2 = None
mouseLeftClick = False
mouseRightClick = False
line1 = []
line = []
countFrames = 0
oldframeTime = 0
fpsRealMean = args.fps
gain = 400
fpsBrightness = 0
scrollValueAccumulatedX = 0

#####################
# Mouse Control Functions
#####################

# Initialize mouse controller
mouse = Controller()

# Function to get screen size using xrandr
def get_screen_size():
    try:
        # Execute xrandr command and capture output
        result = subprocess.run(["xrandr"], capture_output=True, text=True)
        output = result.stdout

        # Filter the line containing the current resolution
        resolution_line = next((line for line in output.splitlines() if '*' in line), None)

        if resolution_line:
            # Find resolution in WxH format, e.g., "1920x1080"
            resolution = next((word for word in resolution_line.split() if 'x' in word), None)
            
            if resolution:
                width, height = map(int, resolution.split('x'))
                return width, height

        # Return default values if resolution detection fails
        return 1920, 1080
    except Exception as e:
        print(f"Error obtaining screen resolution with xrandr: {e}")
        return 1920, 1080  # Default value in case of error

# Get screen size
screen_width, screen_height = get_screen_size()

# Detect Wayland
if os.getenv('XDG_SESSION_TYPE') == 'wayland':
    graphics_system = 'wayland'
else:
    graphics_system = 'xorg'

# Global variables to store the last known mouse position
last_known_x = None
last_known_y = None

# Variables for caching mouse position
cached_mouse_position = (0, 0)
last_mouse_update_time = 0

# Function to get the current mouse position compatible with Xorg and Wayland
def get_mouse_position():
    global last_known_x, last_known_y, cached_mouse_position, last_mouse_update_time
    current_time = time.time()
    
    # Update mouse position once per two seconds
    if current_time - last_mouse_update_time > 2:
        if graphics_system == 'wayland':
            try:
                result = subprocess.run(["kdotool", "getmouselocation", "--shell"], capture_output=True, text=True)
                output = result.stdout
                position = {}

                for line in output.splitlines():
                    if line.startswith("X="):
                        position['X'] = int(line.split('=')[1].strip())
                    elif line.startswith("Y="):
                        position['Y'] = int(line.split('=')[1].strip())

                if 'X' in position and 'Y' in position:
                    last_known_x, last_known_y = position['X'], position['Y']
                cached_mouse_position = (last_known_x, last_known_y)
            except Exception as e:
                print(f"Error obtaining mouse position with kdotool: {e}")
        else:
            last_known_x, last_known_y = mouse.position
            cached_mouse_position = (last_known_x, last_known_y)
        
        last_mouse_update_time = current_time
    
    return cached_mouse_position

# Function to set the mouse position compatible with Xorg and Wayland
def set_mouse_position(delta_x, delta_y):
    global last_known_x, last_known_y, cached_mouse_position, last_mouse_update_time
    if graphics_system == 'wayland':
        current_x, current_y = get_mouse_position()
        new_x = current_x + delta_x
        new_y = current_y + delta_y
        if last_known_x is not None and last_known_y is not None:
            # Ensure the new position does not exceed screen boundaries
            new_x = max(0, min(new_x, screen_width - 1))
            new_y = max(0, min(new_y, screen_height - 1))
        mouse.position = (new_x, new_y)
        
        # Save caches changes in mouse position until detected again with kdotool
        cached_mouse_position = (new_x, new_y)
    else:
        mouse.move(delta_x, delta_y)


#####################
# Tooltip Code
#####################
current_tooltip = None

# Function to run Tkinter in a separate thread
def tkinter_tooltip_main():
    global tkTooltip, current_tooltip
    tkTooltip = tk.Tk()
    tkTooltip.withdraw()  # Hide the main Tkinter window

    def create_tooltip(text, color, bg, mouseX, mouseY):
        global current_tooltip

        # If the text is "hide", destroy the current tooltip
        if text == "hide":
            if current_tooltip:
                current_tooltip.destroy()
            return

        # Destroy any active tooltip before creating a new one
        if current_tooltip:
            current_tooltip.destroy()

        # Create a new Toplevel window for the tooltip
        tooltip = tk.Toplevel(tkTooltip)
        tooltip.overrideredirect(True)  # Remove window decorations
        tooltip.attributes("-topmost", True)  # Keep the window above others
        current_tooltip = tooltip  # Update the active tooltip

        # Calculate the size of the tooltip
        tooltipFontSize = 20
        if text == "":
            tooltipWidth = 20
            tooltipHeight = 20
        elif text == "hide":
            tooltipWidth = 0
            tooltipHeight = 0
        else:
            tooltipWidth = len(text) * tooltipFontSize
            tooltipHeight = tooltipFontSize + 14

        # Adjust the position so that the tooltip does not go off the screen
        screen_width = tooltip.winfo_screenwidth()
        screen_height = tooltip.winfo_screenheight()

        adjusted_mouseX = mouseX
        adjusted_mouseY = mouseY

        if adjusted_mouseX == 'center':
            adjusted_mouseX = screen_width / 2 - tooltipWidth / 2
        elif adjusted_mouseX > screen_width - tooltipWidth - 40:
            adjusted_mouseX = adjusted_mouseX - tooltipWidth - 40
        else:
            adjusted_mouseX = adjusted_mouseX + tooltipWidth + 40

        if adjusted_mouseY == 'center':
            adjusted_mouseY = screen_height / 2 - tooltipHeight / 2
        elif adjusted_mouseY > screen_height - tooltipHeight - 40:
            adjusted_mouseY = adjusted_mouseY - tooltipHeight - 40
        else:
            adjusted_mouseY = adjusted_mouseY + tooltipHeight + 40

        tooltip.geometry(f"{tooltipWidth}x{tooltipHeight}+{int(adjusted_mouseX)}+{int(adjusted_mouseY)}")

        # Create and position the label inside the tooltip
        label = tk.Label(
            tooltip, 
            text=text, 
            fg=color, 
            bg=bg, 
            font=("Ubuntu Mono", tooltipFontSize),
            relief="solid",
            bd=2
        )
        label.pack(expand=True, fill=tk.BOTH)

    def show_tooltip_scheduled(text, color, bg, mouseX, mouseY):
        tkTooltip.after(0, lambda: create_tooltip(text, color, bg, mouseX, mouseY))

    # Expose the show_tooltip function to be globally accessible
    global show_tooltip
    show_tooltip = show_tooltip_scheduled
    
    tkTooltip.mainloop()

# Start the Tkinter thread to manage tooltips
tkinter_thread = threading.Thread(target=tkinter_tooltip_main, daemon=True)
tkinter_thread.start()

# Show message about ready to use
# Get initial screen dimensions using Tkinter
root = tk.Tk()
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.destroy()

# Move mouse to the center of the screen
mouse.position = (screen_width / 2, screen_height / 2)

# Show message about ready to use (moved after tkinter thread starts)
def show_initial_message():
    # time.sleep(0.5)  # Wait for tkinter thread to initialize
    show_tooltip('Loading BigHeadTracker', "#000000", "#ffe600", 'center', 'center')

threading.Thread(target=show_initial_message, daemon=True).start()


#####################
# System Tray with PyQt6
#####################

from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

class TrayIcon(QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        super().__init__(icon, parent)
        self.setToolTip("Accessibility Program")
        self.activated.connect(self.on_tray_activated)
        self.show()

        # Create the menu
        menu = QMenu(parent)
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.on_exit)

        self.setContextMenu(menu)

    def on_tray_activated(self, reason):
        """
        Handle activation (click) events on the tray icon.
        Show the confirmation dialog on left-click.
        """
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            print("Tray icon clicked. Showing confirmation dialog.")
            threading.Thread(target=show_exit_confirmation, daemon=True).start()

    def on_exit(self):
        """
        Handle the exit action from the tray menu.
        """
        print("Exit action triggered. Showing confirmation dialog.")
        threading.Thread(target=show_exit_confirmation, daemon=True).start()

# Function to show exit confirmation dialogs using Tkinter
def show_exit_confirmation():
    # First confirmation dialog
    if messagebox.askyesno("Confirm Exit", "Are you sure you want to exit the program?"):
        # Second confirmation dialog
        if messagebox.askyesno("Final Confirmation", "Are you really sure you want to exit the program?"):
            # User confirmed exit
            global running
            running = False  # Signal the mediapipe loop to stop
            tray_icon.hide()  # Hide the tray icon
            QApplication.quit()  # Quit the PyQt application


import cv2
import mediapipe as mp
from mediapipe.python.solutions.drawing_utils import _normalized_to_pixel_coordinates

# Video Source Classes
class VideoSource:
    def __init__(self, flip=False, display=False, dtype=np.uint8):
        self._name = "VideoSource"
        self._capture = None
        self._display = display
        self._dtype = dtype
        self._flip = flip
        self._window_initialized = False

    @property
    def fps(self):
        return self._capture.get(cv2.CAP_PROP_FPS)

    @property
    def frame_count(self):
        return int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT))

    @property
    def image_size(self):
        return (
            self._capture.get(cv2.CAP_PROP_FRAME_WIDTH),
            self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        )

    def release(self):
        if self._capture is not None:
            self._capture.release()
        if self._window_initialized:
            cv2.destroyAllWindows()
            self._window_initialized = False

    def __iter__(self):
        if self._capture is not None and self._capture.isOpened():
            return self
        raise StopIteration

    def __next__(self):
        if self._capture is None or not self._capture.isOpened():
            raise StopIteration

        ret, frame = self._capture.read()
        if not ret:
            raise StopIteration

        if cv2.waitKey(1) & 0xFF == ord("q"):
            raise StopIteration

        if self._flip:
            frame = cv2.flip(frame, 1)  # Changed to 1 for horizontal flip
            
        if args.webcamToRGB:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        return frame

    def __del__(self):
        self.release()

    def gain(self, gain):
        if self._capture is None:
            return

        props = {
            cv2.CAP_PROP_GAIN: (2 if gain == 1 else -2),
            cv2.CAP_PROP_BRIGHTNESS: (1 if gain == 1 else -1),
            cv2.CAP_PROP_CONTRAST: (2 if gain == 1 else -2),
            cv2.CAP_PROP_GAMMA: (1 if gain == 1 else -2),
            cv2.CAP_PROP_BACKLIGHT: (1 if gain == 1 else -1)
        }

        for prop, value in props.items():
            current = self._capture.get(prop)
            self._capture.set(prop, current + value)

    def show(self, frame, webcamx, webcamy):
        if not self._window_initialized:
            cv2.namedWindow("BigHeadTrack", cv2.WINDOW_GUI_NORMAL)
            self._window_initialized = True
        cv2.imshow("BigHeadTrack", frame)
        cv2.resizeWindow("BigHeadTrack", webcamx, webcamy)

class WebcamSource(VideoSource):
    def __init__(self, camera_id=0, width=1024, height=768, fps=15, autofocus=0, 
                 absolute_focus=75, flip=True, display=False):
        super().__init__(flip, display)
        self._capture = cv2.VideoCapture(camera_id, cv2.CAP_V4L2)
        
        # Set camera properties in a single block
        props = {
            cv2.CAP_PROP_FRAME_WIDTH: width,
            cv2.CAP_PROP_FRAME_HEIGHT: height,
            cv2.CAP_PROP_GAIN: 0,
            cv2.CAP_PROP_EXPOSURE: 1 / (fps / 10000),
            cv2.CAP_PROP_FOURCC: cv2.VideoWriter_fourcc(*"MJPG"),
            cv2.CAP_PROP_FPS: fps,
            cv2.CAP_PROP_AUTO_EXPOSURE: 3,
            cv2.CAP_PROP_FOCUS: absolute_focus / 255
        }

        for prop, value in props.items():
            self._capture.set(prop, value)


# Initialize Video Source
source = WebcamSource(width=args.webcamx, height=args.webcamy, fps=args.fps, camera_id=args.webcamid)


# Function to perform mouse actions
def make_action(action_type):
    global action
    action = action_type
    mouse_position = get_mouse_position()
    
    if action_type == 'pressLeft' and not globals()['stopCursor']:
        show_tooltip('', "#000000", "#00b600", mouse_position[0], mouse_position[1])
        mouse.press(Button.left)

    elif action_type == 'releaseLeft' and not globals()['stopCursor']:
        mouse.release(Button.left)
        show_tooltip('hide', "#000000", "#00b600", mouse_position[0], mouse_position[1])
        globals()['waitFrames'] = int(fpsRealMean / 6)

    elif action_type == 'showOptions1':
        show_tooltip('', "#000000", "#b6b63d", mouse_position[0], mouse_position[1])
        globals()['stopCursor'] = True

    elif action_type == 'releaseOptions1':
        show_tooltip('hide', "#000000", "#b6b63d", mouse_position[0], mouse_position[1])
        globals()['stopCursor'] = False

    elif action_type == 'pressRight' and not globals()['stopCursor']:
        show_tooltip('', "#000000", "#b6b63d", mouse_position[0], mouse_position[1])
        mouse.press(Button.right)

    elif action_type == 'releaseRight' and not globals()['stopCursor']:
        show_tooltip('hide', "#000000", "#b6b63d", mouse_position[0], mouse_position[1])
        mouse.release(Button.right)
        globals()['waitFrames'] = int(fpsRealMean / 2)

    elif action_type == 'clickLeft':
        mouse.press(Button.left)
        mouse.release(Button.left)
        globals()['waitFrames'] = int(fpsRealMean / 2)

    elif action_type == 'clickRight':
        mouse.press(Button.right)
        mouse.release(Button.right)
        globals()['waitFrames'] = int(fpsRealMean / 2)

    elif action_type == 'enableCursor':
        globals()['stopCursor'] = False

    elif action_type == 'pressScrollV':
        show_tooltip('', "#000000", "#25c0ab", mouse_position[0], mouse_position[1])
        # globals()['waitFrames'] = int(fpsRealMean / 2)
    elif action_type == 'releaseScrollV':
        if globals()['stopCursor']:
            globals()['stopCursor'] = False
            globals()['action'] == ''
            show_tooltip('hide', "#000000", "#25c0ab", mouse_position[0], mouse_position[1])
            globals()['waitFrames'] = int(fpsRealMean / 2)
        else:
            show_tooltip('', "#000000", "#25c0ab", mouse_position[0], mouse_position[1])
            globals()['stopCursor'] = True
            globals()['action'] = 'scrollV'
            globals()['waitFrames'] = int(fpsRealMean / 2)

    elif action_type == 'toggleKeyboard':
        subprocess.run(["qdbus", "org.onboard.Onboard", "/org/onboard/Onboard/Keyboard", "org.onboard.Onboard.Keyboard.ToggleVisible"])

#####################
# Distance Calculation Functions
#####################

def calculate_distance2D(landmarks, var_name, top_indices, bottom_indices):
    # Get the X and Y coordinates of the top and bottom points
    top_pointsX = np.array([landmarks[index][0] for index in top_indices])
    bottom_pointsX = np.array([landmarks[index][0] for index in bottom_indices])
    top_pointsY = np.array([landmarks[index][1] for index in top_indices])
    bottom_pointsY = np.array([landmarks[index][1] for index in bottom_indices])

    # Calculate the distance between the top and bottom points
    distance_x = np.sum(bottom_pointsX + 2) - np.sum(top_pointsX + 2)
    distance_y = np.sum(bottom_pointsY + 2) - np.sum(top_pointsY + 2)
    if distance_x < 0:
        distance_x = 0
    if distance_y < 0:
        distance_y = 0

    # Specific calculations for each variable
    if var_name == 'kiss':
        distance = (np.sum(distance_x + distance_y) / globals()['irisDistance'] - 1) * 50
    elif var_name == 'leftEye':
        distance = (distance_x + distance_y) / globals()['overLeftEye'] * 50 - 9
        if distance < 0:
            distance = 0
    elif var_name == 'rightEye':
        distance = (distance_x + distance_y) / globals()['overRightEye'] * 50 - 9
        if distance < 0:
            distance = 0
    else:
        distance = distance_x + distance_y

    # Save the distance in a global variable
    globals()[var_name] = distance

    # Initialize related variables if they don't exist yet
    var_name_old = f"{var_name}Old"
    var_name_mean = f"{var_name}Mean"
    var_name_normalized = f"{var_name}Normalized"
    var_name_confirmation = f"{var_name}Confirmation"
    var_name_clicked = f"{var_name}Clicked"

    if var_name_old not in globals():
        globals()[var_name_mean] = distance
        globals()[var_name_normalized] = distance
        globals()[var_name_old] = distance
        globals()[var_name_confirmation] = 1
        globals()[var_name_clicked] = False

def verify_false_click(var_name, distance_value, confirm_value, action_start, action_end):
    var_confirmation = globals()[f"{var_name}Confirmation"]
    distance = globals()[var_name]

    if globals()['confirmationTimeout'] == 0 and not globals()['clicked']:
        globals()[f"{var_name}Old"] = (globals()[f"{var_name}Old"] * fpsRealMean / 2 + distance) / (fpsRealMean / 2 + 1)

    globals()[f"{var_name}Mean"] = (distance + globals()[f"{var_name}Mean"]) / 2
    globals()[f"{var_name}Normalized"] = (distance + globals()[f"{var_name}Old"]) / 2

    var_mean = globals()[f"{var_name}Mean"]
    var_old = globals()[f"{var_name}Old"]
    var_normalized = globals()[f"{var_name}Normalized"]

    if not globals()[f"{var_name}Clicked"] and not globals()['clicked'] and eyesOpen >= 3 and waitFrames == 0:
        if eyesOpen and distance < var_old * distance_value and not standByClick and ((mousePointXabs < args.slowMouseMoveX and mousePointYabs < args.slowMouseMoveY) or (var_name == 'kiss')):
            
            globals()[f"{var_name}Confirmation"] += 1
            globals()['confirmationTimeout'] = int(fpsRealMean / 3) + confirm_value
            var_confirmation += 1

            if ((var_confirmation >= 1 + confirm_value and eyesOpen == 10) or 
                (var_confirmation >= int(fpsRealMean / 7) + confirm_value and eyesOpen == 5) or 
                (var_confirmation >= int(fpsRealMean / 4) + confirm_value and eyesOpen == 3)) and not globals()['clicked']:
                
                if action_start != 'wait':
                    make_action(action_start)
                
                globals()['clicked'] = True
                globals()[f"{var_name}Clicked"] = True

    if globals()[f"{var_name}Clicked"]:
        if var_mean > var_old * distance_value and distance > var_old * distance_value:
            globals()[f"{var_name}Confirmation"] = 1
            globals()[f"{var_name}Clicked"] = False
            globals()['clicked'] = False
            make_action(action_end)

    if eyesOpen == 0:
        globals()[f"{var_name}Confirmation"] = 1

######################
# Facemesh Parameters
######################
mp_drawing = mp.solutions.drawing_utils
mp_face_mesh = mp.solutions.face_mesh
mp_face_mesh_connections = mp.solutions.face_mesh_connections
drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=0, color=(0, 255, 0))


#####################
# Facemesh ROI Function for auto adjusting brightness
#####################
def get_eyes_roi(frame, landmarks_obj):
    height, width, _ = frame.shape
    left_eye_indices = [224, 193, 128, 229]
    right_eye_indices = [444, 449, 251, 441]

    # Function to get the ROI of an eye based on the indices
    def get_eye_roi(indices):
        eye_roi_array = []
        for index in indices:
            pixelCoordinates = _normalized_to_pixel_coordinates(landmarks_obj.landmark[index].x, landmarks_obj.landmark[index].y, width, height)
            if pixelCoordinates is not None:
                x, y = pixelCoordinates
                eye_roi_array.append((x, y))
        if not eye_roi_array:
            return None
        eye_roi_array = np.array(eye_roi_array)
        eye_roi_array_rect = cv2.boundingRect(eye_roi_array)
        return frame[eye_roi_array_rect[1]:eye_roi_array_rect[1] + eye_roi_array_rect[3],
                     eye_roi_array_rect[0]:eye_roi_array_rect[0] + eye_roi_array_rect[2]]

    # Get ROIs for both eyes
    left_eye_roi = get_eye_roi(left_eye_indices)
    right_eye_roi = get_eye_roi(right_eye_indices)

    # Return the ROI with the smallest area
    if left_eye_roi is not None and right_eye_roi is not None:
        if left_eye_roi.size < right_eye_roi.size:
            return left_eye_roi
        else:
            return right_eye_roi
    elif left_eye_roi is not None:
        return left_eye_roi
    elif right_eye_roi is not None:
        return right_eye_roi
    else:
        return None

#####################
# Mediapipe Processing
#####################

def mediapipe_processing():
    global running, frameNumber, zeroPointX2, zeroPointY2, waitFrames, confirmationTimeout, eyesOpen, clicked
    global mousePointXabsOld, mousePointYabsOld, mousePointXabs, mousePointYabs, slowMove, mousePositionFrameX, mousePositionFrameY
    global maybeScreenLimitX, maybeScreenLimitY, action
    global oldframeTime, fpsReal, fpsRealMean
    global fpsBrightness, gain, scrollValueAccumulatedX  # Add any other globals you modify here
    
    oldframeTime = time.time()  # Initialize oldframeTime
    
    # Initialize face mesh for detecting facial points
    with mp_face_mesh.FaceMesh(
        static_image_mode=False,
        refine_landmarks=True,
        max_num_faces=1,
        min_detection_confidence=0.2,
        min_tracking_confidence=0.2,
    ) as face_mesh:
        while running:
            try:
                frame_rgb = next(iter(source))
            except StopIteration:
                break

            ##############################
            # Auto adjust Brightness, Contrast, Gamma
            ##############################
            if args.autoBrightness:
                fpsBrightness += 1

                if fpsBrightness > fpsRealMean:
                    results = face_mesh.process(frame_rgb)
                    if results.multi_face_landmarks:
                        landmarks_obj = results.multi_face_landmarks[0]
                        landmarks = np.array([(lm.x, lm.y, lm.z) for lm in face_landmarks.landmark])
                        eyes_roi_value = get_eyes_roi(frame_rgb, landmarks_obj)

                        if eyes_roi_value is not None:
                            brightness = np.average(eyes_roi_value)
                            brightness_average = brightness  # Assuming single value

                            if brightness_average < 150:
                                gain = 1
                                source.gain(gain)
                            elif brightness_average > 200:
                                gain = 0
                                source.gain(gain)
                            fpsBrightness = 0
                    else:
                        # No face detected; continue processing and trying to detect a face
                        print("No face detected, trying again...")

            # Calculate FPS
            frameTime = time.time()
            if oldframeTime != 0:
                fpsReal = int(1 / (frameTime - oldframeTime))
                fpsRealMean = (fpsReal + (fpsRealMean * 10)) / 11
            oldframeTime = frameTime

            ############################
            # Process Facemesh results
            ############################
            results = face_mesh.process(frame_rgb)
            if results.multi_face_landmarks:
                ############################
                # Create landmarks
                ############################
                face_landmarks = results.multi_face_landmarks[0]
                landmarks = np.array([(lm.x, lm.y, lm.z) for lm in face_landmarks.landmark])

                if frameNumber < fpsRealMean:
                    frameNumber += 1
                else:
                    if waitFrames > 0:
                        waitFrames -= 1
                    if confirmationTimeout > 0:
                        confirmationTimeout -= 1

                    ##############################################
                    # Mouse movement detection mode 1
                    ##############################################
                    if args.mouseDetectionMode == 1:
                        mouseMoveX = np.linalg.norm(landmarks[6][0] - landmarks[6][2]) * args.mouseSpeedX * 10
                        mouseMoveY = np.linalg.norm(landmarks[6][1] - landmarks[6][2]) * args.mouseSpeedY * 10

                        if zeroPointX2 is None:
                            zeroPointX = mouseMoveX
                            zeroPointY = mouseMoveY
                            zeroPointX2 = mouseMoveX
                            zeroPointY2 = mouseMoveY
                            mousePointXabs = 0
                            mousePointYabs = 0

                        mousePointX = mouseMoveX - zeroPointX2
                        mousePointY = mouseMoveY - zeroPointY2

                        mousePointXabsOld = mousePointXabs
                        mousePointYabsOld = mousePointYabs
                        mousePointXabs = abs(mousePointX)
                        mousePointYabs = abs(mousePointY)

                        if slowMove > 9:
                            slowMove -= 1

                        if (mousePointXabs > args.minimalMouseMoveX or mousePointYabs > args.minimalMouseMoveY) and slowMove < 10:
                            if mousePointXabs < args.slowMouseMoveX and mousePointYabs < args.slowMouseMoveY:
                                mousePointXApply = mousePointX * mousePointXabs / args.slowMouseMoveX
                                mousePointYApply = mousePointY * mousePointYabs / args.slowMouseMoveY
                                slowMove = 11
                            else:
                                mousePointXApply = mousePointX * mousePointXabs / args.slowMouseMoveX
                                mousePointYApply = mousePointY * mousePointYabs / args.slowMouseMoveY

                            if not stopCursor:
                                set_mouse_position(int(mousePointXApply), int(mousePointYApply))

                                mouse_position = get_mouse_position()
                                if mousePositionFrameX == mouse_position[0] and mousePointXabs > 1:
                                    zeroPointX2 -= (zeroPointX2 - mouseMoveX) * 0.1

                                if mousePositionFrameY == mouse_position[1] and mousePointYabs > 1:
                                    zeroPointY2 -= (zeroPointY2 - mouseMoveY) * 0.1

                                mousePositionFrameX, mousePositionFrameY = mouse_position

                    ##############################################
                    # Mouse movement detection mode 2
                    ##############################################
                    elif args.mouseDetectionMode == 2:
                        mouseMoveX = (math.atan((landmarks[1][0] + ((landmarks[454][0] + landmarks[473][0] + landmarks[152][0]) / 3))) * 3)
                        mouseMoveX = mouseMoveX ** 4 * 4

                        mouseMoveY = (math.atan((landmarks[1][1] + ((landmarks[152][1] + landmarks[473][1] + landmarks[34][1]) / 3))) * 3)
                        mouseMoveY = mouseMoveY ** 4 * 4

                        if zeroPointX2 is None:
                            zeroPointX = mouseMoveX
                            zeroPointY = mouseMoveY
                            zeroPointX2 = mouseMoveX
                            zeroPointY2 = mouseMoveY
                            mousePointXabs = 0
                            mousePointYabs = 0

                        mousePointX = mouseMoveX - zeroPointX2
                        mousePointY = mouseMoveY - zeroPointY2

                        mousePointXabsOld = mousePointXabs
                        mousePointYabsOld = mousePointYabs
                        mousePointXabs = abs(mousePointX)
                        mousePointYabs = abs(mousePointY)

                        if slowMove > 9:
                            slowMove -= 1

                        if (mousePointXabs > args.minimalMouseMoveX or mousePointYabs > args.minimalMouseMoveY) and slowMove < 10:
                            if mousePointXabs < args.slowMouseMoveX and mousePointYabs < args.slowMouseMoveY:
                                mousePointXApply = mousePointX * mousePointXabs / args.slowMouseMoveX
                                mousePointYApply = mousePointY * mousePointYabs / args.slowMouseMoveY
                                slowMove = 11
                            else:
                                mousePointXApply = mousePointX * mousePointXabs / args.slowMouseMoveX
                                mousePointYApply = mousePointY * mousePointYabs / args.slowMouseMoveY

                            if not stopCursor:
                                set_mouse_position(int(mousePointXApply), int(mousePointYApply))

                                mouse_position = get_mouse_position()
                                if mousePositionFrameX == mouse_position[0] and mousePointXabs > 1:
                                    zeroPointX2 -= (zeroPointX2 - mouseMoveX) * 0.1

                                if mousePositionFrameY == mouse_position[1] and mousePointYabs > 1:
                                    zeroPointY2 -= (zeroPointY2 - mouseMoveY) * 0.1

                                mousePositionFrameX, mousePositionFrameY = mouse_position

                    ##############################################
                    # Check if using the right eye
                    ##############################################
                    if args.enableRightEye:
                        calculate_distance2D(landmarks, 'overRightEye', [258, 257, 259], [254, 253, 252])
                        calculate_distance2D(landmarks, 'rightEye', [385, 386, 387], [373, 374, 380])

                    if args.enableLeftEye:
                        calculate_distance2D(landmarks, 'overLeftEye', [28, 27, 29], [22, 23, 24])
                        calculate_distance2D(landmarks, 'leftEye', [158, 159, 160], [153, 145, 144])

                    if args.enableKiss:
                        calculate_distance2D(landmarks, 'irisDistance', [469], [476])
                        calculate_distance2D(landmarks, 'kiss', [178, 80, 41], [318, 415, 272])

                    # Check eye conditions to set eyesOpen state
                    if ((leftEye < leftEyeMean * 0.68 and rightEye < rightEyeMean * 0.68) or 
                        (leftEye < leftEyeNormalized * 0.4 and rightEye < rightEyeNormalized * 0.4)) and not clicked:
                        eyesOpen = 0
                        waitFrames = int(fpsRealMean)
                    else:
                        if eyesOpen == 0:
                            eyesOpen = 3

                        if eyesOpen > 0 and leftEye > leftEyeNormalized * 0.8 and rightEye > rightEyeNormalized * 0.8 and not clicked:
                            if (leftEye > leftEyeOld * 0.85 and rightEye > rightEyeOld * 0.85 and 
                                mousePointXabs <= 1 and mousePointYabs <= 1 and 
                                mousePointXabsOld <= 1 and mousePointYabsOld <= 1):
                                eyesOpen = 10
                            else:
                                eyesOpen = 5

                            if ((leftEye < leftEyeNormalized * 0.7 and rightEye < rightEyeNormalized * 0.7 and not clicked) or 
                                (mousePointYabsOld > mousePointYabs and not clicked) or 
                                (mousePointXabsOld > mousePointXabs and not clicked)):
                                eyesOpen = 3

                    if args.enableRightEye and globals()['action'] != 'scrollV':
                        verify_false_click('rightEye', 0.7, 0, 'pressRight', 'releaseRight')

                    if args.enableLeftEye and globals()['action'] != 'scrollV':
                        verify_false_click('leftEye', 0.7, 0, 'pressLeft', 'releaseLeft')

                    if args.enableKiss:
                        verify_false_click('kiss', 0.7, 1, 'pressScrollV', 'releaseScrollV')

                    if action == 'scrollV' and mousePointYabs > args.minimalMouseMoveY:
                        print(f"mousepoint {mousePointYabs}")
                        print(f"args.minimalMouseMoveY {args.minimalMouseMoveY}")

                        scrollValueX = mousePointYApply / fpsRealMean
                        scrollValueAccumulatedX += scrollValueX

                        if scrollValueAccumulatedX > 1 or scrollValueAccumulatedX < -1:
                            mouse.scroll(0, int(-scrollValueAccumulatedX))
                            scrollValueAccumulatedX = 0
                    elif action == 'showOptions1':
                        mouse_position = get_mouse_position()
                        if mousePointXApply < -args.minimalMouseMoveX * 3:
                            show_tooltip('Double Click', "#000000", "#ff00ff", mouse_position[0], mouse_position[1])
                        elif mousePointXApply > args.minimalMouseMoveX * 3:
                            show_tooltip('Hold', "#000000", "#afaaaf", mouse_position[0], mouse_position[1])
                        elif mousePointYApply > args.minimalMouseMoveY * 2:
                            show_tooltip('Middle Button', "#000000", "#4440ff", mouse_position[0], mouse_position[1])
                        elif mousePointYApply < -args.minimalMouseMoveY * 2:
                            show_tooltip('Show Keyboard', "#000000", "#626634", mouse_position[0], mouse_position[1])
                        elif action == 'pressLeft':
                            show_tooltip('', "#000000", "#008eff", mouse_position[0], mouse_position[1])

                    ##############################
                    # Display information on screen
                    ##############################
                    if args.view != 0:
                        ##############################
                        # Prepare the display frame
                        ##############################
                        if args.view == 2:
                            avatar = np.zeros(
                                shape=[args.webcamy, args.webcamx, 3], dtype=np.uint8)
                            showInCv = avatar
                        else:
                            showInCv = frame.copy()

                        cv2.rectangle(showInCv, (0, 0), (300, 300), (0, 0, 0), -1)

                        # Display text with information on the screen
                        cv2.putText(showInCv, f"FPS {int(fpsReal)}", (20, 40),
                                    cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 1)

                        cv2.putText(showInCv, f"Left Eye  {int(leftEye)}", (20, 80),
                                    cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 1)

                        cv2.putText(showInCv, f"Right Eye {int(rightEye)}", (20, 120),
                                    cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 1)

                        cv2.putText(showInCv, f"Horizontal {int(mousePointX)}", (20, 160),
                                    cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 1)

                        cv2.putText(showInCv, f"Vertical {int(mousePointY)}", (20, 200),
                                    cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 1)

                        if args.view > 0:
                            # Center horizontal line
                            cv2.line(showInCv, (0, (int(args.webcamy / 2))), (args.webcamx, (int(args.webcamy / 2))), (255, 255, 255), 1)
                            cv2.line(showInCv, (0, (int(args.webcamy / 2) + 1)), (args.webcamx, (int(args.webcamy / 2) + 1)), (0, 0, 0), 1)

                            # Center vertical line
                            cv2.line(showInCv, (int(args.webcamx / 2), 0), (int(args.webcamx / 2), args.webcamx), (255, 255, 255), 1)
                            cv2.line(showInCv, (int(args.webcamx / 2) + 1, 0), (int(args.webcamx / 2) + 1, args.webcamx), (0, 0, 0), 1)


                    ##############################
                    # Show points on avatar
                    ##############################
                    if args.view == 2:
                        # Left Eye Upper0 / Right Eye Lower0
                        for id in [246, 161, 160, 159, 158, 157, 173, 33, 7, 163, 144, 145, 153, 154, 155, 133, 263, 249, 390, 373, 374, 380, 381, 382, 362, 466, 388, 387, 386, 385, 384, 398]:
                            cv2.circle(showInCv, (int(landmarks[id][0] * args.webcamx), int(landmarks[id][1] * args.webcamy)), 1, (155, 155, 155), 1)

                        # Left Eye Top
                        for id in [158, 159, 160]:
                            cv2.circle(showInCv, (int(landmarks[id][0] * args.webcamx), int(landmarks[id][1] * args.webcamy)), 1, (255, 0, 255), 1)

                        # Left Eye Bottom
                        for id in [144, 145, 163]:
                            cv2.circle(showInCv, (int(landmarks[id][0] * args.webcamx), int(landmarks[id][1] * args.webcamy)), 1, (0, 255, 255), 1)

                        # Right Eye Top
                        for id in [385, 386, 387]:
                            cv2.circle(showInCv, (int(landmarks[id][0] * args.webcamx), int(landmarks[id][1] * args.webcamy)), 1, (255, 0, 255), 1)

                        # Right Eye Bottom
                        for id in [373, 374, 380]:
                            cv2.circle(showInCv, (int(landmarks[id][0] * args.webcamx), int(landmarks[id][1] * args.webcamy)), 1, (0, 255, 255), 1)

                        # Nose and iris
                        for id in [1, 468, 473]:
                            cv2.circle(showInCv, (int(landmarks[id][0] * args.webcamx), int(landmarks[id][1] * args.webcamy)), 1, (55, 255, 55), 1)

                        # Face Oval
                        for id in [10, 338, 338, 297, 297, 332, 332, 284, 284, 251, 251, 389, 389, 356, 356, 454, 454, 323, 323, 361, 361, 288, 288, 397, 397, 365, 365, 379, 379, 378, 378, 400, 400, 377, 377, 152, 152, 148, 148, 176, 176, 149, 149, 150, 150, 136, 136, 172, 172, 58, 58, 132, 132, 93, 93, 234, 234, 127, 127, 162, 162, 21, 21, 54, 54, 103, 103, 67, 67, 109, 109, 10]:
                            cv2.circle(showInCv, (int(landmarks[id][0] * args.webcamx), int(landmarks[id][1] * args.webcamy)), 1, (0, 255, 0), 1)

                        # Lips Top Inner
                        for id in [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308]:
                            cv2.circle(showInCv, (int(landmarks[id][0] * args.webcamx), int(landmarks[id][1] * args.webcamy)), 1, (255, 0, 255), 1)

                        # Lips Bottom Inner
                        for id in [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308]:
                            cv2.circle(showInCv, (int(landmarks[id][0] * args.webcamx), int(landmarks[id][1] * args.webcamy)), 1, (0, 255, 255), 1)


                        # Lips Top Outer
                        for id in [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291]:
                            cv2.circle(showInCv, (int(landmarks[id][0] * args.webcamx), int(landmarks[id][1] * args.webcamy)), 1, (255, 0, 255), 1)

                        # Lips Bottom Outer
                        for id in [146, 91, 181, 84, 17, 314, 405, 321, 375, 291]:
                            cv2.circle(showInCv, (int(landmarks[id][0] * args.webcamx), int(landmarks[id][1] * args.webcamy)), 1, (0, 255, 255), 1)

                        ##############################
                        # Draw facemesh landmarks
                        ##############################
                        mp_drawing.draw_landmarks(
                            image=showInCv,
                            landmark_list=face_landmarks,
                            connections=mp_face_mesh_connections.FACEMESH_IRISES,
                            landmark_drawing_spec=drawing_spec,
                            connection_drawing_spec=drawing_spec,
                        )
                        source.show(showInCv, args.webcamx, args.webcamy)

                        ##############################
                        # Plot graphic
                        ##############################
                        if args.plot == 1:  # Plot the left eye
                            if countFrames == 10:
                                import matplotlib.pyplot as plt  # to plot graphics
                                from collections import deque  # to plot graphics
                                pts_plot = deque(maxlen=64)
                                pts_plot.append(leftEye)  # Append the blink value to the list of points to be plotted
                                min_value = -0.003
                                max_value = 0.015
                            if countFrames > 70:  # Wait some frames before plotting to avoid initial spikes
                                # Ensure plotting_ear is defined or replace with actual plotting logic
                                pass
                                # line1 = plotting_ear(pts_plot, line1, min_value, max_value)  # Call function to plot the graph
                            countFrames += 1

                        elif args.plot == 2:  # Plot the right eye
                            if countFrames == 10:
                                import matplotlib.pyplot as plt  # to plot graphics
                                from collections import deque  # to plot graphics
                                pts_plot = deque(maxlen=64)
                                pts_plot.append(rightEyeBlink)  # Append the blink value to the list of points to be plotted
                                min_value = -0.003
                                max_value = 0.015
                            if countFrames > 70:  # Wait some frames before plotting to avoid initial spikes
                                # Ensure plotting_ear is defined or replace with actual plotting logic
                                pass
                                # line1 = plotting_ear(pts_plot, line1, min_value, max_value)  # Call function to plot the graph
                            countFrames += 1
                            
                        if not running:
                            break

# Initialize PyQt6 Application for System Tray
app_qt = QApplication(sys.argv)

# Load an icon image (ensure 'icon.svg' exists in your working directory)
icon_path = resource_path("icon.png")  # Replace with your icon path
if not os.path.exists(icon_path):
    # Create a simple red square as a placeholder if the icon does not exist
    placeholder = Image.new('RGB', (64, 64), color = 'red')
    placeholder.save(icon_path)

icon_qt = QtGui.QIcon(icon_path)

# Create and display the tray icon
tray_icon = TrayIcon(icon_qt)

# Global flag to control the application's running state
running = True

# Start the mediapipe processing in a separate thread
mediapipe_thread = threading.Thread(target=mediapipe_processing, daemon=True)
mediapipe_thread.start()

# Show message about ready to use
show_tooltip('Ready', "#000000", "#00b600", 'center', screen_height / 2)

#####################
# Start the PyQt6 Event Loop
#####################
sys.exit(app_qt.exec())
