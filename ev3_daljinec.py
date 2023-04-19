#!/usr/bin/env python3

# Copyright 2020, Nejc Ilc
# Using ev3-python3 library ev3_dc for sending direct commands to EV3:
# https://github.com/ChristophGaukel/ev3-python3
#
# Large left motor must be on port A
# Large right motor must be on port D
# (optional) Medium motor must be on port C

import contextlib
# Disable pygame message
with contextlib.redirect_stdout(None):
    import pygame
import pygame.time
import os
import sys
import ev3_dc as ev3
from thread_task import Sleep, Task
import requests
import json

SERVER_URL = 'http://192.168.0.3:8088/game/9125'

# Maximum frames per second
FPS = 30
# ID of a EV3 robot to use when no arguments are given
ROBOT_ID_DEFAULT = 'RED'

# Using medium motor?
USE_MEDIUM_MOTOR = False

# Define motors ports
MOTOR_LEFT_PORT = ev3.constants.PORT_B
MOTOR_RIGHT_PORT = ev3.constants.PORT_C
MOTOR_MEDIUM_PORT = ev3.constants.PORT_A

# Map of robots id and MAC
id2MAC = {
    'R1':  '00:16:53:40:A2:BD',
    'R2':  '00:16:53:41:44:AC',
    'R13': '00:16:53:46:B6:A1',
    'RED': '00:16:53:46:C4:03',
    'BLUE': '00:16:53:46:8F:57',
}

# Movement constants
SPEED_MAX = 100
SPEED_HALF = 50
SPEED_LOW = 20
TURN_SOFT = 50
CLAWS_DEGREES = 370

# Game window size
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800

# Path to images
IMG_PATH = 'img'
# Images filenames
IMG_BACKGROUND = 'background.png'
IMG_ARROW_UP = 'arrow_up.png'
IMG_ARROW_DOWN = 'arrow_down.png'
IMG_ARROW_LEFT = 'arrow_left.png'
IMG_ARROW_RIGHT = 'arrow_right.png'
IMG_SPACE_ACTION = 'space_action.png'

# For fonts display
def make_font(fonts, size):
    available = pygame.font.get_fonts()
    # get_fonts() returns a list of lowercase spaceless font names
    choices = map(lambda x:x.lower().replace(' ', ''), fonts)
    for choice in choices:
        if choice in available:
            return pygame.font.SysFont(choice, size)
    return pygame.font.Font(None, size)
    
_cached_fonts = {}
def get_font(font_preferences, size):
    global _cached_fonts
    key = str(font_preferences) + '|' + str(size)
    font = _cached_fonts.get(key, None)
    if font == None:
        font = make_font(font_preferences, size)
        _cached_fonts[key] = font
    return font

_cached_text = {}
def create_text(text, fonts, size, color):
    global _cached_text
    key = '|'.join(map(str, (fonts, size, color, text)))
    image = _cached_text.get(key, None)
    if image == None:
        font = get_font(fonts, size)
        image = font.render(text, True, color)
        _cached_text[key] = image
    return image

def exit_app():
    # TODO: review
    motorLeft.stop(brake=False)
    motorRight.stop(brake=False)
    if USE_MEDIUM_MOTOR:
        motorMedium.stop(brake=False)
    pygame.quit()
    sys.exit(0)

def beep():
    ops = b''.join([
        ev3.opSound,
        ev3.TONE,
        ev3.LCX(1),    # VOLUME
        ev3.LCX(440),  # FREQUENCY
        ev3.LCX(1000),  # DURATION
    ])
    my_ev3.send_direct_cmd(ops)

def beep2():
    #jukebox.play_tone("f'''", duration=1, volume=100)
    music = jukebox.song(ev3.TRIAD)
    music.start()

def claws_open():
    if not motorMedium.busy:
        t = motorMedium.move_to(CLAWS_DEGREES, speed=SPEED_HALF,brake=False) + Task(print, args=('open done',))
        t.start()

def claws_close():
    if not motorMedium.busy:
        t = motorMedium.move_to(-CLAWS_DEGREES, speed=SPEED_HALF, brake=False) + Task(print, args=('close done',))
        t.start()

def help():
    print('EV3 Commander 2')
    print('(C) 2020, Nejc Ilc')
    print('Uporaba:\n \
    ./daljinec.py -h\t\t\tizpiše tole\n \
    ./daljinec.py\t\t\tpreko WiFi se bomo povezali na privzetega robota % s\n \
    ./daljinec.py id\t\t\tpreko WiFi se bomo povezali na robota z oznako "id"\n \
    ./daljinec.py serial protocol\tpreko "protocol" ("WiFi", "Bluetooth" ali "Usb") se bomo povezali na robota s serijsko številko "serial"\n' % (ROBOT_ID_DEFAULT)
    )
# Arguments check
if len(sys.argv) == 1:
    robot_id = ROBOT_ID_DEFAULT
    print('Povezujem se na robota z oznako '+ robot_id+'.')
    
elif len(sys.argv) == 2:
    if sys.argv[1] == '-h' or sys.argv[1] == '-help':
        help()
        sys.exit(0)
    else:
        robot_id = sys.argv[1]

elif len(sys.argv) == 3:
    MAC = sys.argv[2]
    PROTOCOL = sys.argv[3]
else:
    help()
    raise RuntimeError("Napacno stevilo argumentov.")

if robot_id:
    #PROTOCOL = ev3.BLUETOOTH
    PROTOCOL = ev3.WIFI
    
    if robot_id in id2MAC:
        MAC = id2MAC[robot_id]
    else:
        raise RuntimeError("Napacen ID robota.")
else:
    robot_id = MAC 


# Connect to EV3 device
my_ev3 = ev3.EV3(protocol=PROTOCOL, host=MAC, verbosity=1)
#robot = ev3.TwoWheelVehicle(radius_wheel=0.056, tread = 0.15, ev3_obj=my_ev3, port_left=MOTOR_LEFT_PORT, port_right=MOTOR_RIGHT_PORT)

motorLeft = ev3.Motor(port=MOTOR_LEFT_PORT, ev3_obj=my_ev3)
motorRight = ev3.Motor(port=MOTOR_RIGHT_PORT, ev3_obj=my_ev3)

if USE_MEDIUM_MOTOR:
    motorMedium = ev3.Motor(port=MOTOR_MEDIUM_PORT, ev3_obj=my_ev3)
    motorMedium.position = 0

# For playing sounds and controlling LEDs
jukebox = ev3.Jukebox(ev3_obj=my_ev3)
jukebox.verbosity = 0


# Start pygame window
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption('EV3 daljinec 2 | Robot '+ robot_id)

# Font that will be used - first one that exists on a system.
font_preferences_sans = [
        "Calibri",
        "Arial",
        "Tahoma"]
font_preferences_mono = [
        "Courier",
        "DejaVuSansMono",
        "Monospace"]

text_commands = create_text("S smernimi tipkami premikaj robota | <SPACE>: troblja | <ENTER>: akcija | <Q>: izhod", font_preferences_sans, 20, (50, 50, 50))

# Prepare images
img_bg = pygame.image.load(os.path.join(IMG_PATH, IMG_BACKGROUND)).convert()
img_up = pygame.image.load(os.path.join(IMG_PATH, IMG_ARROW_UP)).convert()
img_down = pygame.image.load(os.path.join(IMG_PATH, IMG_ARROW_DOWN)).convert()
img_left = pygame.image.load(os.path.join(IMG_PATH, IMG_ARROW_LEFT)).convert()
img_right = pygame.image.load(os.path.join(IMG_PATH, IMG_ARROW_RIGHT)).convert()
img_space = pygame.image.load(os.path.join(IMG_PATH, IMG_SPACE_ACTION)).convert()


speed_left = 0
speed_right = 0
dir_left = 0
dir_right = 0
is_claws_open = True
is_up = False
is_down = False
is_left = False
is_right = False
is_space = False
is_ctrl = False
is_quit = False

c = pygame.time.Clock()
headers = {'Accept': 'application/json'}

d = {'RED': '25', 'BLUE': '27'}
robot_name = d[robot_id]

try:
    while True:
        r = requests.get(SERVER_URL, headers=headers)
        game_state = json.loads(r.content)

        fuel = game_state['teams'][robot_name]
        game_on = game_state['game_on']
        print(fuel)
        

        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                exit_app()
            if fuel > 0 and game_on:
                if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
                    keys = pygame.key.get_pressed()
                    is_up = keys[pygame.K_UP]
                    is_down = keys[pygame.K_DOWN]
                    is_left = keys[pygame.K_LEFT]
                    is_right = keys[pygame.K_RIGHT]
                    is_space = keys[pygame.K_SPACE]
                    is_ctrl = keys[pygame.K_RETURN]
                    is_quit = keys[pygame.K_q]

                    speed_left = 0
                    speed_right = 0
                    dir_left = 0
                    dir_right = 0

                    # Quit
                    if is_quit:
                        exit_app()
                    
                    # Horn
                    if is_space:                    
                        beep()

                    # Claws
                    if is_ctrl:
                        if USE_MEDIUM_MOTOR:
                            if is_claws_open:
                                claws_close()
                                is_claws_open = False
                            else:
                                claws_open()
                                is_claws_open = True

                    # Forward
                    if is_up:
                        speed_left = SPEED_MAX
                        dir_left = 1
                        speed_right = SPEED_MAX
                        dir_right = 1

                    if is_up and is_left:
                        speed_left = SPEED_MAX - TURN_SOFT
                    if is_up and is_right:
                        speed_right = SPEED_MAX - TURN_SOFT

                    # Rotate on place
                    if not is_up and not is_down and is_left:
                        speed_left = SPEED_HALF
                        dir_left = -1
                        speed_right = SPEED_HALF
                        dir_right = 1
                        
                    if not is_up and not is_down and is_right:
                        speed_left = SPEED_HALF
                        dir_left = 1
                        speed_right = SPEED_HALF
                        dir_right = -1
                    
                    # Backward
                    if is_down:
                        speed_left = SPEED_MAX
                        dir_left = -1
                        speed_right = SPEED_MAX
                        dir_right = -1
                    if is_down and is_left:
                        speed_left = SPEED_MAX - TURN_SOFT
                    if is_down and is_right:
                        speed_right = SPEED_MAX - TURN_SOFT
                    
                    if speed_left == 0 and speed_right == 0:
                        motorLeft.stop(brake=False)
                        motorRight.stop(brake=False)
                    else:
                        motorLeft.start_move(speed=speed_left, direction=dir_left, ramp_up_time=0.5)
                        motorRight.start_move(speed=speed_right, direction=dir_right, ramp_up_time=0.5)
                        #print(speed_left, dir_left, speed_right, dir_right)

        # Update screen
        screen.fill((255, 255, 255))
        screen.blit(img_bg, (0, 0))
        screen.blit(text_commands, (20, WINDOW_HEIGHT - 40))
        if is_up:
            screen.blit(img_up, (0,0))
        if is_down:
            screen.blit(img_down, (0,0))
        if is_left:
            screen.blit(img_left, (0,0))
        if is_right:
            screen.blit(img_right, (0,0))
        if is_space:
            screen.blit(img_space, (0,0))
        pygame.display.flip()
        c.tick(FPS)        


except SystemExit as err:
    print("Izhod.")
