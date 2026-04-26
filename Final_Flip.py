import RPi.GPIO as GPIO
import time

# -----------------------
# PINS
# -----------------------
RPWM = 18   # Forward
LPWM = 23   # Reverse

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(RPWM, GPIO.OUT)
GPIO.setup(LPWM, GPIO.OUT)

# PWM setup
rpwm = GPIO.PWM(RPWM, 1000)
lpwm = GPIO.PWM(LPWM, 1000)

rpwm.start(0)
lpwm.start(0)

# -----------------------
# FUNCTIONS
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
# Flip Logic
# -----------------------
try:
    print("Starting flip")

    # Device moves forward to move the object
    forward(75)   # 75 for forward motion
    time.sleep(0.5)

    stop()
    time.sleep(0.5)

    # Device moves backward to move the object and flip
    reverse(80)
    time.sleep(0.5)

    stop()

    print("Done")

except KeyboardInterrupt:
    pass

finally:
    stop()
    rpwm.stop()
    lpwm.stop()
    GPIO.cleanup()
