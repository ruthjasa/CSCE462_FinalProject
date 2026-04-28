'''
Pan Flip Device - Motor Controller
Team 12: Ruth Jasadiredja, Lucas Kim
CSCE 462 Final Project
'''

import RPi.GPIO as GPIO
import time

# -----------------------
# PIN CONFIGURATION
# -----------------------
RPWM = 18   # Forward
LPWM = 23   # Reverse

# -----------------------
# MOTION PARAMETERS
# -----------------------
FORWARD_SPEED = 75
REVERSE_SPEED = 80

FORWARD_TIME = 0.5
STOP_TIME = 0.5
REVERSE_TIME = 0.5

# -----------------------
# SETUP
# -----------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(RPWM, GPIO.OUT)
GPIO.setup(LPWM, GPIO.OUT)

rpwm = GPIO.PWM(RPWM, 1000)
lpwm = GPIO.PWM(LPWM, 1000)

rpwm.start(0)
lpwm.start(0)

# -----------------------
# MOTOR FUNCTIONS
# -----------------------
def stop():
    rpwm.ChangeDutyCycle(0)
    lpwm.ChangeDutyCycle(0)

def forward(speed):
    lpwm.ChangeDutyCycle(0)
    rpwm.ChangeDutyCycle(speed)

def reverse(speed):
    rpwm.ChangeDutyCycle(0)
    lpwm.ChangeDutyCycle(speed)

# -----------------------
# FLIP FUNCTION
# -----------------------
def flip():
    """
    Executes one pan flip motion:
    1. Forward motion positions the object
    2. Pause stabilizes the system
    3. Reverse motion provides impulse to flip
    """
    forward(FORWARD_SPEED)
    time.sleep(FORWARD_TIME)

    stop()
    time.sleep(STOP_TIME)

    reverse(REVERSE_SPEED)
    time.sleep(REVERSE_TIME)

    stop()

# -----------------------
# MAIN
# -----------------------
try:
    print("Starting flip")
    flip()
    print("Done")

except KeyboardInterrupt:
    print("Interrupted")

finally:
    stop()
    rpwm.stop()
    lpwm.stop()
    GPIO.cleanup()
