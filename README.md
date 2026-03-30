# CSCE 462 Final Project — Pan Flip Device (Team 12)

**Team:** Ruth Jasadiredja, Lucus Kim

A motorized four-bar linkage that flips food in a pan and catches it. The input link is driven by a brushed DC motor with encoder feedback; a Raspberry Pi runs a 5-phase position-controlled FSM to execute repeatable flip cycles.

---

## Mechanical Design

Four-bar linkage (all wood):

| Link | Total length | Center-to-center |
|------|-------------|-----------------|
| Ground (fixed to base) | 9.75" | 8.5" |
| Input (motor-driven at B) | 5.875" | 5.0" |
| Coupler (pan attaches here) | 16.25" | 15.0" |
| Output (free pivot at A) | 13.55" | 12.3" |

All pivot holes are 1" diameter for bearings. The input link motor end has a 5 mm hex hole to mate with the gearbox output shaft.

Pan: 8" diameter, 6" handle, 769 g.

---

## Hardware

| Component | Part | Notes |
|-----------|------|-------|
| Microcontroller | Raspberry Pi | 3.3 V GPIO |
| Motor | REV HD Hex Motor (REV-41-1600) | 12 V brushed DC, 6000 RPM free, 8.5 A stall |
| Gearbox | REV UltraPlanetary (3:1 × 4:1 × 5:1) | 60:1 total → ~109 RPM output, 5.75 Nm stall |
| Motor driver | HiLetGo BTS7960 43 A H-Bridge | Dual-PWM direction control |
| Encoder | Built into HD Hex Motor | 28 counts/rev at motor shaft = 1,680 counts/rev at output |
| Power | 12 V battery (motor), separate supply (Pi) | Shared GND |

---

## Wiring

### BTS7960 → Raspberry Pi

| BTS7960 pin | Signal | Raspberry Pi GPIO |
|-------------|--------|-------------------|
| RPWM (1) | Forward PWM | GPIO 12 (hardware PWM) |
| LPWM (2) | Reverse PWM | GPIO 13 (hardware PWM) |
| R_EN (3) | Forward half-bridge enable | GPIO 16 |
| L_EN (4) | Reverse half-bridge enable | GPIO 20 |
| R_IS (5) | Current sense | leave unconnected |
| L_IS (6) | Current sense | leave unconnected |
| VCC (7) | Logic supply | Pi 3.3 V or 5 V |
| GND (8) | Logic ground | Pi GND |

### BTS7960 Power

| BTS7960 terminal | Connection |
|-----------------|------------|
| B+ | 12 V battery positive |
| B− | 12 V battery negative (share GND with Pi) |
| M+ | Motor positive terminal |
| M− | Motor negative terminal |

### Encoder → Raspberry Pi

| Encoder wire | Connection |
|-------------|------------|
| VCC | Pi 3.3 V |
| GND | Pi GND |
| Channel A | GPIO 23 |
| Channel B | GPIO 24 |

### Optional Trigger Button

Wire a momentary push-button between **GPIO 21** and **GND**. The internal pull-up is enabled in software; the button is active LOW. Set `BUTTON_PIN = None` in `panflip.py` to disable and run in continuous auto-loop mode instead.

---

## Software

### Files

| File | Description |
|------|-------------|
| `panflip.py` | Main motor controller — encoder FSM, full flip cycle |
| `control_setup` | Early prototype using a single servo-style PWM signal (time-based, no encoder). Kept for reference only; superseded by `panflip.py`. |

---

### `panflip.py` Architecture

#### Encoder ISR

`_encoder_isr` is registered on both edges of channel A (`GPIO.BOTH`). On each edge it samples channel B to determine direction, incrementing or decrementing `_encoder_pos` under a threading lock. `get_pos()` and `zero_encoder()` are the public interface to the encoder state.

#### `setup()` / `teardown()`

`setup()` must be called once before any motor command. It configures all GPIO pins, starts both PWM channels at 0% duty, enables the BTS7960 half-bridges, and attaches the encoder interrupt. `teardown()` stops PWM, releases GPIO, and should always be called on exit (the `finally` block in `__main__` guarantees this).

#### `drive_forward()` / `drive_reverse()`

These set RPWM or LPWM duty cycle while holding the opposite channel at 0. Duty is clamped to a minimum of `MIN_DUTY` (15%) when non-zero, preventing the motor from stalling under load at very low commanded speeds.

#### `move_to(target, fast_speed, slow_speed)`

Bang-bang position controller with two-speed approach:

- Runs at `fast_speed` until within `APPROACH_ZONE` ticks of the target.
- Switches to `slow_speed` for the final approach.
- Returns `True` when within `DEADBAND` ticks of the target.
- Returns `False` (and stops the motor) on two fault conditions:
  - **Timeout:** move takes longer than `MOTION_TIMEOUT` seconds.
  - **Stall:** encoder position doesn't change by more than 2 ticks within `STALL_TIMEOUT` (0.5 s), indicating a mechanical jam or encoder failure.

#### `flip_cycle()`

Executes one complete flip-and-return as a 5-phase FSM:

| Phase | Target | Speed | Purpose |
|-------|--------|-------|---------|
| 1 RAMP_UP | 50% of arc (`RAMP_END_TICKS`) | 50% | Gentle launch from home |
| 2 FLIP | 80% of arc (`ACCEL_END_TICKS`) | 80% | Full-speed throw |
| 3 RAMP_DOWN | apex (`TICKS_TO_APEX`) | 35% → 21% | Decelerate into apex |
| 4 APEX | — | stopped | 0.20 s dwell while food is airborne |
| 5 RETURN | home (`TARGET_HOME`) | 55% → 33% | Return to start |

Returns `True` on success. Any phase returning `False` from `move_to()` propagates as a fault.

---

### Tunable Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TICKS_TO_APEX` | 400 | Encoder ticks from home to flip apex — **must be measured empirically** |
| `FLIP_SPEED` | 0.80 | Main arc speed (0.0–1.0 fraction of full PWM) |
| `RAMP_UP_SPEED` | 0.50 | Gentle launch speed |
| `RAMP_DOWN_SPEED` | 0.35 | Approach speed near apex |
| `RETURN_SPEED` | 0.55 | Return-to-home speed |
| `APPROACH_ZONE` | 60 ticks | Distance at which the slow approach speed engages |
| `DEADBAND` | 6 ticks | Position tolerance for "at target" |
| `DWELL_APEX` | 0.20 s | Hold time at apex (food in air) |
| `MIN_DUTY` | 15% | Minimum PWM duty to guarantee movement under load |
| `STALL_TIMEOUT` | 0.5 s | Time without position change before declaring a stall |
| `BUTTON_PIN` | 21 | GPIO for manual flip trigger; `None` for auto-loop |

---

### Calibration (first run)

1. Build and wire the full assembly.
2. In `panflip.py` `__main__`, uncomment:
   ```python
   print_encoder_live(20)
   raise SystemExit("Set TICKS_TO_APEX above, then re-run.")
   ```
3. Run the script and manually push the arm through the full flip arc by hand.
4. Note the tick count printed when the pan reaches the apex.
5. Set `TICKS_TO_APEX` to that value, re-comment the two lines above, and re-run.

---

### Running

```bash
python panflip.py
```

- **Button mode** (`BUTTON_PIN = 21`): press the trigger button to execute one flip cycle.
- **Auto mode** (`BUTTON_PIN = None`): continuously flips every 3 seconds.
- **Ctrl-C** stops the loop cleanly and releases GPIO.

On a fault (stall or timeout), the script waits 5 seconds, re-zeros the encoder, and retries.

---

## Current Status

Week 5 — integration week, combining software, electronics, and physical hardware for first full tests. `TICKS_TO_APEX` is a placeholder (400) and must be calibrated on the physical build before running the flip loop.
