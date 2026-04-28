# CSCE 462 Final Project — Pan Flip Device (Team 12)

**Team:** Ruth Jasadiredja, Lucus Kim

A motorized four-bar linkage that flips food in a pan and catches it. The input link is driven by a brushed DC motor with encoder feedback; a Raspberry Pi runs a 5-phase position-controlled FSM to execute repeatable flip cycles.

---

## Mechanical Design

Four-bar linkage (all wood):

| Link | Total length | Center-to-center |
|------|-------------|-----------------|
| Ground (fixed to base) | 15.5" | 8.5" |
| Input (motor-driven at B) | 5.875" | 5.0" |
| Coupler (pan attaches here) | 16.25" | 15.0" |
| Output (free pivot at A) | 9.5" | 12.3" |

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
| Power | 12 V battery (motor), separate supply (Pi) | Shared GND |

---

## Wiring

### BTS7960 → Raspberry Pi

| BTS7960 pin | Signal | Raspberry Pi GPIO |
|-------------|--------|-------------------|
| RPWM (1) | Forward PWM | GPIO 18 (hardware PWM) |
| LPWM (2) | Reverse PWM | GPIO 23 (hardware PWM) |
| R_EN (3) | Forward half-bridge enable | 5 V |
| L_EN (4) | Reverse half-bridge enable | 5 V |
| R_IS (5) | Current sense | leave unconnected |
| L_IS (6) | Current sense | leave unconnected |
| VCC (7) | Logic supply | leave unconnected |
| GND (8) | Logic ground | Pi GND |

### BTS7960 Power

| BTS7960 terminal | Connection |
|-----------------|------------|
| B+ | 12 V battery positive |
| B− | 12 V battery negative (share GND with Pi) |
| M+ | Motor positive terminal |
| M− | Motor negative terminal |

---

## Software

### Files

| File | Description |
|------|-------------|
| `Final_Flip.py` | Main motor controllor logic, time-based code. |
| `control_setup.py` | Early prototype using a single servo-style PWM signal (time-based, no encoder). Kept for reference only. |
| `panflip.py` | Early prototype using encoder logic. Found to be too inaccurate and unstable. Kept for reference only.| 

---

### `Final_Flip.py` Architecture

#### GPIO + PWM Initialization

The program begins by configuring the Raspberry Pi GPIO pins in BCM mode and disabling warnings. Two PWM outputs are created on pins RPWM (GPIO18) and LPWM (GPIO23) at 1 kHz to control motor direction through the BTS7960 driver. Both PWM channels start at 0% duty cycle to ensure the motor is initially stopped.

#### Motor Control Layer (forward, reverse, stop)

These three functions directly control motor direction:

- forward(speed): Activates RPWM while disabling LPWM, producing clockwise/forward rotation.
- reverse(speed): Activates LPWM while disabling RPWM, producing counterclockwise/reverse rotation.
- stop(): Sets both PWM signals to 0% duty cycle, immediately stopping motion.

Speed is passed as a PWM duty cycle percentage (0–100), which determines motor torque and velocity.

#### Flip Sequence Logic (Main Control Flow)

The system executes a single deterministic flip cycle in sequence:

1. Forward motion
  - forward(75) drives the linkage forward for 0.5 seconds.
  - This positions the pan to push the object forward and upward.
2. Pause / stabilization
  - stop() halts motion briefly (0.5 s).
  - This allows momentum to settle before reversing.
3. Reverse motion (flip action)
  - reverse(80) applies a stronger backward torque.
  - This creates the “kick” motion required to flip the object.
4. Final stop
  - Motor is stopped and held idle.

This sequence is not continuous control; it is an open-loop timed motion profile.

#### Timing-based Motion Control

Instead of sensors or feedback (e.g., encoder control), the system relies entirely on fixed delays (time.sleep()):

- Forward duration: 0.5 s
- Pause duration: 0.5 s
- Reverse duration: 0.5 s

This makes the system simpler but sensitive to load changes, battery voltage, and friction.

#### Safety and Cleanup (try / finally)

The program is wrapped in a try-except-finally structure:

- KeyboardInterrupt allows manual stopping via Ctrl+C
- finally ensures:
  - motor is stopped
  - PWM channels are safely shut down
  - GPIO pins are released (GPIO.cleanup())

This prevents the motor from continuing to run or GPIO pins from locking after execution.

---

### System Behavior Summary
The full system implements a two-phase open-loop flip motion:

- Phase 1: Forward preload motion (positioning + energy buildup)
- Phase 2: Reverse impulse motion (flip execution)

No sensor feedback is used; behavior is entirely determined by PWM intensity + timing.
