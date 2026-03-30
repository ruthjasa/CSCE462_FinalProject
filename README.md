# CSCE462_FinalProject
Project: Pan Flip Device — CSCE 462 Final Project (Team 12)
Building a four-bar linkage device that flips food in a pan and catches it. The four-bar is made of wood with the following dimensions:

Ground link: 9.75" total, 8.5" center-to-center (fixed to base)
Input link: 5.875" total, 5.0" center-to-center (driven by motor at Point B)
Coupler link: 16.25" total, 15.0" center-to-center (pan attaches here)
Output link: 13.55" total, 12.3" center-to-center (free pivot at Point A)
All holes are 1" diameter for bearings except the input link motor end which is a 5mm hex hole

Hardware:

Raspberry Pi (control system)
REV UltraPlanetary Gearbox Kit & HD Hex Motor (REV-41-1600) — brushed DC 12V motor, 6000 RPM free speed, 8.5A stall, with 3 cartridges (3:1, 4:1, 5:1) stacked for 60:1 reduction giving ~109 RPM output and 5.75 Nm stall torque. Output is a 5mm hex shaft.
BTS7960 H-bridge motor driver
12V battery for motor, separate battery for Pi
Built-in encoder on HD Hex Motor: 28 counts/rev at motor shaft = 1,680 counts/rev at output shaft after 60:1 gearbox
Pan: 8" diameter, 6" handle, 769g

Wiring:

12V battery → BTS7960 B+ and B−
BTS7960 B− → Pi GND (shared ground)
BTS7960 MOTOR+/− → JST-VH motor power cable
Pi GPIO18 → RPWM, GPIO19 → LPWM, GPIO24 → R_EN, GPIO25 → L_EN, Pi 5V → VCC
Encoder JST-PH: pin1 → Pi 3.3V, pin2 → Pi GND, pin3 → GPIO17 (channel A), pin4 → GPIO27 (channel B)

Software:

Python on Raspberry Pi
Time-based FSM with states: idle, ramp-up, flip-through, ramp-down, return-to-start
Key tunable variables: flip_speed (PWM duty cycle), ramp_time, hold_time, return_speed, settle_time
Encoder used to track output shaft position (counts) and verify return to start position
BTS7960 controlled via two PWM signals (RPWM/LPWM) + two enable pins (R_EN/L_EN)

Current status: Week 5 — integration week, combining software, electronics, and physical hardware for first full tests.