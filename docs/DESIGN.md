# Design notes

How each part of the simulator maps to the course, and why every sensor sits
where it sits. Numbers are the defaults in `sim/config.py`.

## 1. The robot

Differential drive, body radius 0.20 m, wheel base 0.30 m, wheel radius 0.05 m.
Two DC motors (12 V, 25 rad/s per V, 30:1 gearbox, 0.15 s time constant) with a
4 % speed mismatch between them, as real motors have. Underwater the same class
drives two thrusters.

```
            [camera, tilted 15° down]
    cliffFL                       cliffFR        IR switches 0.12 m ahead of the front corners
        irL      irC      irR                    3 IR PSDs facing forward across the body width
   S2 ---------------------------- S0            sonar ring, S0 straight ahead, 45° apart (cave/Mars)
   cliffL   gyro  accel  compass/sun   cliffR    side cliff switches
   S4       [optical flow / DVL]       S7
        cliffRL                  cliffRR         rear cliff switches (escape manoeuvres reverse!)
                     S6                          S4/S6: rear-looking sonars
```

## 2. Actuators and control (Actuators 1-2, Control)

* **PWM → speed is not linear.** `DCMotor.effective_voltage()` has a static
  friction dead band (duty < 0.06 gives nothing) and a power-law curve; the
  steady-state speed drops with load. `calibration_table()` reproduces the
  lecture's "measure the speed at each duty cycle" table; the plot
  `results/pid_step_response.png` shows it.
* **Encoders** are on the motor shaft before the gearbox (16 ticks × 30 =
  480 ticks per wheel revolution). Speed feedback is the tick delta per
  control step — quantised, exactly what a pulse-counting register gives.
* **Controllers** implement the lecture's formulas: on-off, on-off with
  hysteresis, and the incremental PID
  `R_n = R_{n-1} + Kp(e_n − e_{n−1}) + Ki(e_n + e_{n−1})/2 + Kd(e_n − 2e_{n−1} + e_{n−2})`.
  The step-response demo shows the P controller's steady-state error and how
  PI/PID remove it and reject the load step at t = 3 s.
* **Driving straight**: an extra I-controller integrates the difference of
  the two encoder *positions* and feeds it back to both wheel set-points
  (lecture Fig. 5.16). Wheel slip is applied after the motors, so the
  encoders never see it: that is the physical reason dead reckoning drifts.

## 3. Sensors (Sensors 1-2)

Every sensor carries its course classification (`SensorClass`): local/global,
internal/external, active/passive, binary/analog/digital. Analog sensors go
through a 10-bit A/D converter (`ADC`). Any sensor can be set to *stuck*,
*dead* or *noisy* at run time (the *Inject fault* column of the Sensors tab).

| Sensor | Class | Placement and why |
|---|---|---|
| Sonar ring, 8 × 45° (12 × 30° underwater) | external, active, digital (time of flight) | Around the body at bumper height so no part of the body shadows a cone. Modelled with a 15° cone (5 rays), **specular loss** when the incidence angle exceeds 65–78° (the lecture's "obstacle seems further away"), **cross-talk** between neighbours, and timing noise proportional to range. Main mapping sensor. |
| IR PSD × 3, all facing forward | external, active, analog | Spread across the body width so anything the body is about to hit lies in a beam (the sonar cones at 0° and ±45° leave a blind strip exactly there). Output `V = 24/(d_cm + 4)` is non-linear and is linearised by a per-sensor **lookup table built by calibration**; below 6 cm the characteristic folds back, so the sensor is recessed by that distance. Only the near 70 % of the range is trusted: at long range the curve is flat and ADC noise alone can fake an echo. |
| Cliff switches × 6 (front corners, sides, rear corners) | external, active, binary | A horizontal range sensor cannot see a hole. The front pair looks ahead of the wheels; the **rear pair exists because every escape manoeuvre reverses**; the side pair because the body can brush a pit while turning. One missing pair cost us a rover in testing. |
| Bumpers × 2 | external, passive, binary | A strip across the front, left and right halves: the pair tells the escape behaviour which way to turn (lecture). Contact on the side of the body (a current pushing the robot into a wall) does not press a *front* bumper. |
| Encoders × 2 | internal, passive, digital | On the motor shafts. Speed feedback and dead reckoning. |
| Compass (cave, underwater) | internal, passive, digital, 1° | Absolute heading, bounds the drift of gyro integration. In the cave a local magnetic disturbance is modelled (iron in the rock). **Not mounted on Mars** — no usable global magnetic field. |
| Sun sensor (Mars) | external, passive, digital | What real Mars rovers use for absolute heading. Same role as the compass. |
| Gyro (yaw rate) | internal, passive, digital | At the centre of mass. Has a constant bias: integrating it alone drifts, which is why the heading filter learns the bias while the robot stands still (the 1.5 s calibration at mission start) and corrects with the compass/sun sensor. |
| Accelerometer / inclinometer | internal, passive, digital | Tilt from the gravity vector, low-pass filtered because body acceleration cannot be separated from tilt in one sample (lecture: inclinometers lag). The SLOPE behaviour refuses crater rims steeper than 11°. |
| Camera, tilted down | external, passive, digital | Sees a 16×16 patch of the ground ahead. Input to the terrain classifier. Darkness adds noise; the headlights cost 4 W. |
| Optical flow (cave, Mars) / DVL (underwater) | external, active, digital | Looks at the ground and measures how it really moves under the body — immune to wheel slip (Mars sand: 25 %) and, underwater, the only odometry there is (thrusters have no ground contact). The fused estimator uses it for displacement; the encoders remain the "dead reckoning" reference. |
| Battery monitor | internal, passive, analog | Terminal voltage through a divider into the ADC; feeds the return-home decision. |
| Light sensor + headlights (cave) | external, passive, analog | Darkness → headlights on → more power → shorter mission. |
| Gas sensor (cave) | external, passive, analog, first-order lag | Gas pockets become high-cost zones in the planner (not walls). |
| Pressure sensor (underwater) | external, passive, analog | Depth. |

## 4. Localisation

Three estimates run side by side and are drawn on the map: encoders-only
dead reckoning (red), the fused estimate (green) and the true pose (yellow,
true world only). Typical result after 400 s: encoders-only 2–13 m off,
fused 0.05–0.3 m off. The "Encoders only" option in the menu makes the robot
*use* the drifting estimate, so the map tears apart visibly.

## 5. Mapping

Log-odds occupancy grid, 0.2 m cells. A sonar echo clears the cells along the
beam axis (−0.4), weakly clears the cone edges over the near 70 % of the
reading, and adds +0.6 to the cell just *beyond* the echo distance (the
echo comes from the surface; the obstacle is behind it). A cell needs two
echoes to count as occupied, so single cross-talk spikes never create walls.
A missing echo marks nothing: it is usually a lost reflection, not free
space. The IRs confirm free space close to the body.

## 6. Behaviour (subsumption)

Highest active layer wins:

1. `STOP` — fell into a pit or battery empty.
2. `ESCAPE` — bumper: reverse 0.7 s (or turn, if a rear cliff sensor fires), turn away from the side that hit, blacklist the target.
3. `CLIFF` — any cliff switch: back away from the edge, turn away from it, mark the hazard.
4. `SLOPE` — tilt > 11°: back off.
5. `SCAN` — mission start: 1.5 s still (gyro bias), one full turn (fill the map).
6. `AVOID` — sonar/IR closer than 0.32 m ahead or 0.14 m diagonally: steer to the freer side. Uses an **on-off controller with hysteresis** (switch off only once the way is clearly open) and reverses out after 3 s of continuous avoidance.
7. `HOME` — the energy needed to get back (distance × power / speed × 1.6 safety) exceeds what is left, or the map is complete.
8. `EXPLORE` — follow the A* path to the explorer's target (pure-pursuit, 0.35 m look-ahead).
9. `WANDER` — random walk (the lecture's Monte-Carlo walk) when there is nothing else to do.

## 7. Planning and exploration

* Cost map: occupied + hazard cells inflated by the robot radius
  (configuration space), +1.5 next to the band so paths stay centred,
  unknown cells cost 8× (allowed, strongly avoided), × terrain cost from the AI.
* A*, 8-connected, octile heuristic, no corner cutting.
* **Nearest frontier**: clusters of free cells touching unknown space; go to
  the closest reachable one and stay committed to it (otherwise the robot
  oscillates between two equally near frontiers).
* **DFS with backtracking**: waypoints 1 m apart; try forward, left, right,
  back; a dead end pops the stack and drives back to the previous node
  (counted as a backtracking event). When the stack is exhausted but unknown
  space remains, restart from the nearest frontier.
* **Utility (AI)**: frontier score = information gain / (terrain-weighted
  distance + 1) − hazard penalty − battery penalty.

## 8. AI

* **Terrain classifier**: Random Forest on 18 texture features (mean, std,
  gradients, edge fraction, ripple spectra, lag-1 autocorrelation, crack
  fraction, skewness, kurtosis, 8-bin histogram) of the camera patch. Trained
  on 3 500 synthetic patches, ≈ 86 % accuracy on held-out patches, ~70–90 %
  live (darker scenes are harder). Predicted class → planner cost
  (sand 2.5, mud 4, bedrock 0.8, rock 6, pit 8).
* **Fault detector**: per ranging sensor, over a 60-sample window: *stuck*
  (no change while moving, and not at max range), *dead* (pinned at max
  range while both neighbours see something close), *noisy* (jitter ≫ rated
  noise). A faulty sensor is dropped from mapping and avoidance.
* **Utility explorer**: see §7.

## 9. Remote operation and the radio link

A `TELEOP` layer sits between `AVOID` and `HOME` in the subsumption stack.
When the operator chooses *assisted* or *manual* it takes the place of
`EXPLORE`; in *assisted* mode every layer above it still overrides the
operator (shared control), in *manual* mode `ESCAPE`, `CLIFF`, `SLOPE` and
`AVOID` are switched off and only `STOP` remains. A watchdog zeroes the
command one second after the last one received.

Commands (from the keyboard, a game controller, or the phone/tablet console
served by `sim/teleop/server.py`) go through `RadioLink` (`sim/comms.py`): a base
station at the start point, signal strength
`(1 − 0.65 (d / range)²) · (1 − wall_loss · walls)` smoothed like an RSSI,
packets dropped with 50 % probability when *weak* and always when *lost*,
delivered after the environment's latency (Mars 2 s, underwater 0.4 s). Lost
for three seconds → `link_fallback`: autonomy takes over according to the
operator's *Link lost* choice (return home by default: the rover drives back
into range on its own; or explore / wait) until a command arrives again.
Calibration: cave range 18 m, 5 % loss per wall cell (near half ok, middle
weak, far corner lost); underwater 16 m, 5 %, 0.4 s; Mars 60 m, 2 %, 2 s.

The console page never drives the robot directly: physical commands (drive,
steer, lights, stop, return home) only enter this link, and the page says so
when one is dropped. Console *settings* (who drives, link-lost action, top
speed) describe how the operator wants to work and apply at once. The car-like
response (keyboard, triggers, ✕ / △ with the arrows) is `v = v_max · y|y|`,
`ω = 1.0 · x|x| · (1 − 0.35|y|)`. The joystick and a controller's left stick
use *point-to-go* instead (`Mission.steer_to_drive`): the stick gives a
direction on the north-up map, the rover turns towards it with
`turn = sign(e)·√min(1, |e|/60°)` (e = that direction minus the estimated
heading) and drives with `|stick| · max(0, (cos e − 0.35)/0.65)`, so it only
moves once it roughly faces the target and circling the stick spins it.

**Alerts** (`sim/alerts.py`), shared by the desktop status bar and the console
header: the raw conditions (stuck in mud or sand, weak or lost link, low
battery, gas, a failed sensor, too dark for the camera, paused, over) are
debounced 0.8 s, the alert shown is held at least 3 s unless a more serious
one takes over after 1 s, and every start and end goes to an event log.
Alerts travel as a key and arguments, so each interface words them in its own
language (English or Egyptian Arabic).
The **Radio link** tab draws the base station, the walls on the line of
sight and the RSSI, and logs every packet with the sender's address; the maps
draw the line of sight coloured by the link state.

## 10. Things we learned the hard way (all reproducible with the fault buttons)

* Without rear and side cliff sensors the rover reverses or brushes into craters.
* A median filter on the sonar lags during turns and paints walls in the wrong
  place: better to reject spikes in the map than in time.
* IR readings near maximum range are noise, not obstacles.
* A front bumper must not fire on side contact, or a current pushing the robot
  along a wall triggers an endless reverse-into-the-wall loop.
* A gyro bias of 0.006 rad/s is 20° after a minute: calibrate while still, and
  keep an absolute heading reference (compass or sun sensor).
