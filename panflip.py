"""
Pan Flip Device - Motor Controller
Team 12: Ruth Jasadiredja, Lucus Kim
CSCE 462 Final Project

Hardware:
  - HiLetGo BTS7960 43A H-Bridge motor driver
  - REV Ultraplanetary brushed DC motor w/ built-in quadrature encoder
  - Raspberry Pi (3.3V GPIO)

BTS7960 wiring to Raspberry Pi:
  RPWM  (pin 1) -> GPIO 12  (hardware PWM, forward)
  LPWM  (pin 2) -> GPIO 13  (hardware PWM, reverse)
  R_EN  (pin 3) -> GPIO 16  (enable forward half-bridge)
  L_EN  (pin 4) -> GPIO 20  (enable reverse half-bridge)
  R_IS  (pin 5) -> leave unconnected
  L_IS  (pin 6) -> leave unconnected
  VCC   (pin 7) -> Pi 3.3V or 5V
  GND   (pin 8) -> Pi GND

  B+  -> 12V battery positive
  B-  -> 12V battery negative  (share GND with Pi)
  M+  -> Motor positive terminal
  M-  -> Motor negative terminal

Ultraplanetary Encoder wiring to Raspberry Pi:
  Encoder A   -> GPIO 23
  Encoder B   -> GPIO 24
  Encoder VCC -> Pi 3.3V   (Ultraplanetary encoder is 3.3V safe)
  Encoder GND -> Pi GND

BTS7960 control inputs accept 3.3-5V so Pi GPIO levels are fine directly.
"""

import RPi.GPIO as GPIO
import time
import threading

# ─────────────────────────────────────────────────────────
# Pin Assignments
# ─────────────────────────────────────────────────────────
RPWM_PIN = 12   # Forward PWM  -> BTS7960 RPWM (pin 1)
LPWM_PIN = 13   # Reverse PWM  -> BTS7960 LPWM (pin 2)
R_EN_PIN = 16   # Forward enable -> BTS7960 R_EN (pin 3)
L_EN_PIN = 20   # Reverse enable -> BTS7960 L_EN (pin 4)

ENC_A    = 23   # Encoder channel A
ENC_B    = 24   # Encoder channel B

PWM_FREQ = 1000  # Hz (BTS7960 supports up to 25 kHz; 1 kHz is smooth and safe)

# ─────────────────────────────────────────────────────────
# Motion Parameters  (tune after physical build)
# ─────────────────────────────────────────────────────────
#
# To find TICKS_TO_APEX:
#   1. Uncomment print_encoder_live() near the bottom and run the script
#   2. Manually push the 4-bar arm through the full flip arc by hand
#   3. Note the tick count printed when the pan is at the apex
#   4. Set TICKS_TO_APEX to that number, re-comment print_encoder_live()
#
TICKS_TO_APEX   = 400    # ticks: home -> flip apex  (measure empirically)
TARGET_HOME     = 0      # ticks at resting/home position

RAMP_UP_SPEED   = 0.50   # 0.0-1.0 fraction of full PWM duty
FLIP_SPEED      = 0.80   # speed during main arc
RAMP_DOWN_SPEED = 0.35   # speed approaching apex
RETURN_SPEED    = 0.55   # speed returning home

APPROACH_ZONE   = 60     # ticks from target to switch to slow speed
DEADBAND        = 6      # +/- ticks: "close enough" to stop

DWELL_APEX      = 0.20   # seconds to hold at apex (food is airborne)
DWELL_HOME      = 0.10   # seconds to settle at home before next flip

MOTION_TIMEOUT  = 4.0    # seconds: abort move if it takes longer than this

# ─────────────────────────────────────────────────────────
# Encoder State  (updated by GPIO interrupt)
# ─────────────────────────────────────────────────────────
_encoder_pos  = 0
_encoder_lock = threading.Lock()
_last_enc_a   = 0

def _encoder_isr(channel):
    """Quadrature decoder ISR -- fires on every edge of channel A."""
    global _encoder_pos, _last_enc_a
    a = GPIO.input(ENC_A)
    b = GPIO.input(ENC_B)
    if a != _last_enc_a:
        with _encoder_lock:
            if a == b:
                _encoder_pos += 1
            else:
                _encoder_pos -= 1
        _last_enc_a = a

def get_pos():
    with _encoder_lock:
        return _encoder_pos

def zero_encoder():
    global _encoder_pos
    with _encoder_lock:
        _encoder_pos = 0

# ─────────────────────────────────────────────────────────
# GPIO & PWM Setup
# ─────────────────────────────────────────────────────────
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(RPWM_PIN, GPIO.OUT)
GPIO.setup(LPWM_PIN, GPIO.OUT)
GPIO.setup(R_EN_PIN, GPIO.OUT)
GPIO.setup(L_EN_PIN, GPIO.OUT)
GPIO.setup(ENC_A,    GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(ENC_B,    GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Both enable lines must be HIGH for the BTS7960 to drive the motor
GPIO.output(R_EN_PIN, GPIO.HIGH)
GPIO.output(L_EN_PIN, GPIO.HIGH)

# Two independent PWM channels, one per direction
rpwm = GPIO.PWM(RPWM_PIN, PWM_FREQ)
lpwm = GPIO.PWM(LPWM_PIN, PWM_FREQ)
rpwm.start(0)   # 0% duty = stopped
lpwm.start(0)

# Interrupt on both edges of ENC_A for full quadrature decoding
GPIO.add_event_detect(ENC_A, GPIO.BOTH, callback=_encoder_isr)

# ─────────────────────────────────────────────────────────
# Low-Level Motor Commands
# ─────────────────────────────────────────────────────────
def stop():
    """Coast to stop: both PWM channels to 0%."""
    rpwm.ChangeDutyCycle(0)
    lpwm.ChangeDutyCycle(0)

def drive_forward(speed: float):
    """
    Forward direction (flip stroke).
    speed 0.0-1.0. RPWM gets the duty; LPWM stays at 0.
    """
    duty = max(0.0, min(1.0, speed)) * 100.0
    lpwm.ChangeDutyCycle(0)
    rpwm.ChangeDutyCycle(duty)

def drive_reverse(speed: float):
    """
    Reverse direction (return stroke).
    speed 0.0-1.0. LPWM gets the duty; RPWM stays at 0.
    """
    duty = max(0.0, min(1.0, speed)) * 100.0
    rpwm.ChangeDutyCycle(0)
    lpwm.ChangeDutyCycle(duty)

# ─────────────────────────────────────────────────────────
# Position-Controlled Move
# ─────────────────────────────────────────────────────────
def move_to(target: int, fast_speed: float, slow_speed: float,
            timeout: float = MOTION_TIMEOUT) -> bool:
    """
    Drive motor until encoder reaches target (+/- DEADBAND).

    Uses fast_speed until within APPROACH_ZONE ticks, then slow_speed
    for the final approach. Returns True on success, False on timeout.
    """
    t0 = time.time()
    while True:
        pos = get_pos()
        err = target - pos

        if abs(err) <= DEADBAND:
            stop()
            return True

        if time.time() - t0 > timeout:
            stop()
            print(f"[FAULT] move_to({target}) timed out at pos={pos}")
            return False

        spd = slow_speed if abs(err) < APPROACH_ZONE else fast_speed

        if err > 0:
            drive_forward(spd)
        else:
            drive_reverse(spd)

        time.sleep(0.002)   # 2 ms control loop

# ─────────────────────────────────────────────────────────
# Flip Cycle  (5-phase FSM)
# ─────────────────────────────────────────────────────────
def flip_cycle(verbose: bool = True) -> bool:
    """
    One complete flip-and-return:
      Phase 1  RAMP_UP   -- gentle launch from home to mid-travel
      Phase 2  FLIP      -- full speed through main arc
      Phase 3  RAMP_DOWN -- decelerate into apex
      Phase 4  APEX      -- dwell while food is airborne
      Phase 5  RETURN    -- drive back to home

    Returns True on success, False if any phase faults.
    """
    mid    = TICKS_TO_APEX // 2
    slowpt = int(TICKS_TO_APEX * 0.80)

    def log(msg):
        if verbose:
            print(f"[FLIP] {msg}  pos={get_pos()}")

    log("-- starting flip --")

    log("Phase 1: RAMP_UP")
    if not move_to(mid, fast_speed=RAMP_UP_SPEED, slow_speed=RAMP_UP_SPEED):
        return False

    log("Phase 2: FLIP")
    if not move_to(slowpt, fast_speed=FLIP_SPEED, slow_speed=FLIP_SPEED):
        return False

    log("Phase 3: RAMP_DOWN")
    if not move_to(TICKS_TO_APEX,
                   fast_speed=RAMP_DOWN_SPEED,
                   slow_speed=RAMP_DOWN_SPEED * 0.6):
        return False

    stop()
    log(f"Phase 4: APEX -- holding {DWELL_APEX}s")
    time.sleep(DWELL_APEX)

    log("Phase 5: RETURN")
    if not move_to(TARGET_HOME,
                   fast_speed=RETURN_SPEED,
                   slow_speed=RETURN_SPEED * 0.6):
        return False

    stop()
    time.sleep(DWELL_HOME)
    log("-- flip complete --\n")
    return True

# ─────────────────────────────────────────────────────────
# Calibration Helper
# ─────────────────────────────────────────────────────────
def print_encoder_live(duration: float = 15.0):
    """
    Stream encoder ticks to the console for `duration` seconds.
    Use this once after building the arm to measure TICKS_TO_APEX.
    """
    print(f"[CAL] Streaming encoder for {duration}s -- move the arm by hand:")
    t_end = time.time() + duration
    try:
        while time.time() < t_end:
            print(f"  pos = {get_pos():6d} ticks", end="\r", flush=True)
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    print(f"\n[CAL] Final position: {get_pos()} ticks")

# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Pan Flip Device -- BTS7960 + Ultraplanetary")
    print("============================================")

    # STEP 1 (first time only): uncomment these two lines to calibrate,
    # find TICKS_TO_APEX, then re-comment before running the flip loop.
    #
    # print_encoder_live(20)
    # raise SystemExit("Set TICKS_TO_APEX above, then re-run.")

    zero_encoder()
    print(f"Encoder zeroed. TICKS_TO_APEX = {TICKS_TO_APEX}")
    print("Starting flip loop. Press Ctrl-C to stop.\n")

    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"-- Cycle #{cycle} --")
            ok = flip_cycle(verbose=True)
            if not ok:
                print("[WARN] Cycle faulted -- waiting 5 s before retry")
                time.sleep(5.0)
                zero_encoder()
            else:
                time.sleep(3.0)

    except KeyboardInterrupt:
        print("\nStopped by user.")

    finally:
        stop()
        rpwm.stop()
        lpwm.stop()
        GPIO.cleanup()
        print("GPIO cleaned up.")