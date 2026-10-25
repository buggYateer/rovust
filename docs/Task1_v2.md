# Team Project – Robotics

**Dr. Elshaimaa Nabil Nada**

**Students Names:**
1. Ahmed Hamed Mohamed
2. Aml Hesham Hosny
3. Tassneem Amin Gamil
4. Kholoud Waleed Attia
5. Donia Essam Fathy
6. Mazen Mohamed Hussien
7. Mohamed Osama Salah
8. Mohamed Elsayed Mohamed
9. Mahmoud Ahmed Abdelghani

# Task 1

**Project Title:** Multi-Environment Autonomous Exploration Rover: A Sensor-Driven Python Simulation from Motor Control to Mapping

## Abstract / Project Definition

Autonomous exploration of unknown environments is a core challenge in robotics: a robot must move safely, avoid obstacles, decide where to go next, and build a map of what it discovers, all without a pre-existing map and without GPS, exactly the situation of a rover on Mars, a robot in a collapsed mine, or a vehicle in a flooded cave. This project addresses the challenge with a software-only exploration rover that is designed, programmed, and tested entirely as a simulation in Python. What distinguishes this project from a pure path-planning demo is that the robot is simulated from the bottom up, following the structure of the Robotics course: the rover is a differential-drive vehicle whose two DC motors are driven through an H-bridge by PWM signals; each motor carries an incremental shaft encoder whose tick count feeds a discrete PID velocity controller, and a second controller compares the two encoder counts so that the robot drives straight despite motor mismatch and wheel slip. On top of the actuators sits a complete on-board sensor suite, chosen and placed according to the sensor classification studied in the course (internal/external, active/passive, binary/analog/digital): a ring of sonar sensors with a realistic narrow cone, specular reflection, and cross-talk; forward infrared position-sensitive devices with a non-linear response corrected by a calibrated lookup table and a mechanical minimum-range limit; downward-facing infrared cliff detectors at the front corners that protect the rover from craters and pits that no horizontal range sensor can see; binary bumper (tactile) switches as the last line of defence; a compass and a gyroscope/accelerometer unit (MPU6050-style) that correct the heading drift of encoder-based dead reckoning; and a forward camera whose images are classified by a small machine-learning model into terrain types (sand, rock, bedrock, mud) so that terrain cost enters the planner. Raw sensor readings are simulated with noise, quantised through a modelled A/D converter, and may be deliberately faulted at run time to show how the controller tolerates a failed sensor. The robot's behaviour is organised as a subsumption architecture in which low-level reflexes (bumper escape, cliff stop, sonar-based obstacle avoidance) override the higher-level exploration behaviour, and in which a human operator can take the place of the exploration layer: the rover can be driven remotely from a phone or tablet over a simulated radio link whose signal weakens with distance and with every wall between the rover and its base station, drops commands when weak and, when lost, hands control back to the autonomy so the rover waits, explores alone or returns home (on Mars the link also carries a two-second delay, the classic argument for on-board decision making); in assisted mode the safety reflexes keep overriding the operator, in manual mode they are switched off to show what they were doing. The exploration behaviour which chooses targets either by frontier-based exploration or by Depth-First Search with backtracking, plans paths with A* on a cost map, and fuses encoder, gyro, and compass data to estimate its own position while building an occupancy grid (unknown / free / occupied). Instead of a separate project per scenario, we build one general engine and a set of selectable environments: when the program starts, the user chooses a cave (narrow branching corridors, dead ends, darkness and short sensing range), a planetary surface such as Mars (open terrain, rocks, craters, sandy ground with high wheel slip), or optionally an underwater site (currents that push the vehicle, sonar instead of light-based sensing). Each environment is only a configuration that defines the map, terrain costs, sensor ranges, noise levels, and slip model, while the motor control, sensing, estimation, and decision logic stay the same. Simulation is the right tool here because building a physical robot for every one of these environments would be expensive, slow, and risky, while a simulator allows safe, repeatable, and measurable experiments. The system is implemented in Python with a Qt (PySide6) desktop interface, NumPy and SciPy for grid maps and signal processing, scikit-learn for the terrain classifier, and a small built-in web server for the operator console on a phone or tablet. The interface shows the true world next to the robot's own belief map, the sonar cones and IR beams, a live panel of every sensor reading, the PWM duty cycle and the PID response of each motor, and statistics such as area coverage, steps, path length, backtracking events, collisions, and localisation error. We will build the system in stages: motor and PID control, sensors and A/D, dead reckoning and sensor fusion, mapping, exploration and planning, the AI terrain classifier, and finally the interface and experiments. The same rover is then tested in every environment, comparing the frontier and DFS strategies under identical conditions and measuring how much each sensor contributes by switching it off. Our hypothesis is that nearest-frontier exploration covers more area with fewer steps in open environments such as the planet surface, whereas DFS with backtracking performs better in corridor-like environments such as the cave, and that heading correction from the gyroscope and compass is the single most important factor for keeping the built map consistent; both claims will be verified by experiment. Overall, the project demonstrates that one modular robot, built from the actuator and sensor level up, can explore several unknown environments simply by changing its configuration, while connecting the main topics of the Robotics course: actuators and PWM, encoders and feedback control, sensor types and interfacing, robot behaviour and subsumption, navigation, mapping, path planning, and decision making.

## Objectives

1. Simulate a differential-drive rover at the actuator level: DC motors, H-bridge direction, PWM speed, encoder feedback, PID velocity control, and straight-line driving control.
2. Model a realistic on-board sensor suite with correct placement, physical limitations, noise, A/D quantisation, and fault injection.
3. Estimate the robot's pose by dead reckoning corrected by gyroscope and compass, and build an occupancy-grid map of an unknown environment.
4. Implement a subsumption behaviour architecture with frontier-based and DFS exploration, A* path planning, and safe return to the start point.
5. Add an AI terrain classifier (camera images → terrain class) that feeds the path-planning cost map.
6. Run the same robot in several environments (cave, Mars, underwater) and evaluate the strategies and sensors with measured experiments.
7. Add remote operation (assisted and manual driving from a phone or tablet) over a simulated radio link with range, obstruction, latency and loss, and a safe fallback to autonomy when the link is lost.

## System Architecture

| Layer | Content | Course topic |
|---|---|---|
| Actuators | 2 DC motors + gearbox, H-bridge (forward / reverse / brake), PWM duty cycle → speed calibration table, motor load and slip model | Actuators 1 & 2 |
| Motor control | Encoder ticks → measured speed, discrete PID velocity loop per motor, I-controller on encoder difference for driving straight, speed ramp for position control | Control |
| Sensors | Sonar ring, IR PSD, IR cliff detectors, bumpers, encoders, compass, gyro/accelerometer, camera, battery; A/D quantisation; polling vs interrupt-style events | Sensors 1 & 2 |
| Localisation | Dead reckoning from encoders; heading corrected by gyro + compass; comparison of true, odometry-only, and corrected paths | Sensors 2 |
| Mapping | Occupancy grid (unknown / free / occupied) from sonar and IR beams, terrain layer from the AI classifier, hazard layer (cliffs, gas) | Navigation |
| Behaviour | Subsumption: Bumper escape > Cliff stop > Slope refuse > Obstacle avoidance > Teleoperation (operator) > Return home (battery) > Explore | Robot Behaviour |
| Communication | Radio link to a base station at the start point: signal vs distance and walls, packet loss, latency; watchdog; fallback to autonomy on link loss | Robot Behaviour (communication) |
| Planning | Frontier-based exploration vs DFS with backtracking; A* on a cost map with obstacle inflation | Navigation / Decision making |
| AI | Terrain classification of camera patches (Random Forest / small CNN); utility-based frontier scoring; sensor-fault detection | Extension |
| Environments | Cave, Mars, Underwater as configuration files (map, terrain costs, sensor ranges, noise, slip, currents) | – |
| Interface | Qt desktop application: mission setup, true world vs belief map, live sensor table with fault injection, PWM/PID plots, statistics, dark/light mode; operator console web page for phone/tablet (joystick inside a sonar ring, camera, map, link and battery); headless batch mode for experiments | – |

## On-board Sensors and Placement

| Sensor | Type (course classification) | Placement | Justification |
|---|---|---|---|
| Sonar ring (8 × 45°, or 5 front + 2 rear) | External, active, analog (time-of-flight) | Around the body at bumper height | Main range sensor for mapping and avoidance; simulated with narrow cone, specular reflection at shallow angles, and cross-talk between neighbours |
| IR PSD × 3 (all facing forward) | External, active, analog → lookup table | Front, spread across the body width, recessed so no object can come closer than the minimum range | Anything the body is about to hit lies in a beam (the sonar cones leave a blind strip there); non-linear output calibrated per sensor, as in the lecture |
| IR cliff detectors × 6 | External, active, binary | Front corners, sides, rear corners, pointing down | Horizontal sensors cannot see craters or pits; the front pair stops the robot before the wheel reaches the edge, the rear pair protects the escape manoeuvres (which reverse), the side pair protects turns |
| Bumpers × 2 (left / right) | External, passive, binary (tactile) | Front left and front right | Last line of defence; left/right pair tells the robot which way to turn away |
| Shaft encoders × 2 | Internal, passive, digital (2-phase incremental) | On each motor shaft before the gearbox | Speed feedback for PID; dead reckoning; direction from phase order |
| Compass (cave, underwater) / Sun sensor (Mars) | Internal, passive, digital | Top centre, away from motors | Absolute heading; cancels the unbounded drift of dead reckoning. Mars has no usable magnetic field, so a sun sensor takes the compass's role |
| Optical flow (cave, Mars) / DVL (underwater) | External, active, digital | Underside, looking at the ground | Measures true ground speed, immune to wheel slip; underwater it is the only odometry (thrusters have no ground contact) |
| Gyro + accelerometer (MPU6050) | Internal, passive, digital (I2C) | Centre of mass | Angular rate integrated to heading; tilt detection to refuse steep slopes |
| Camera | External, passive, digital | Front, tilted ~15° down | Sees the ground ahead; input to the AI terrain classifier |
| Battery monitor | Internal, passive, analog | On-board | Triggers the return-home behaviour |
| Light sensor + headlights (cave) | External, passive, analog | Front | Darkness reduces camera range and increases power use |
| Gas sensor (cave) | External, passive, analog | Top | Hazard layer; the planner avoids dangerous zones |
| Sonar / pressure / DVL (underwater) | External, active | Replaces light-based sensors | Shows that the sensor suite changes with the environment while the control logic does not |

## Experiments

- Frontier vs DFS exploration in every environment, 20 random seeds each: coverage over time, steps, path length, backtracking events, collisions, energy.
- Localisation: true path vs odometry-only vs gyro/compass-corrected path, measured as position error over time.
- Sensor ablation: switch each sensor off (or fault it) and measure the effect on collisions and map quality.
- PID tuning: step response of the velocity controller for several gain settings, following the tuning procedure of the course.
- Remote operation: assisted vs manual driving into obstacles and near craters; behaviour of the rover when the radio link is lost (wait / explore / return home) in each environment.

## Tools

Python 3, PySide6 / Qt (desktop interface), NumPy and SciPy (grids and signals), scikit-learn (terrain classifier), Matplotlib (experiment plots), standard-library HTTP server (operator console).

## Work Plan and Team Roles

| Stage | Deliverable | Members |
|---|---|---|
| 1 | World model, differential drive, motors, PWM, encoders, PID, driving straight | 2 |
| 2 | Sensor suite with noise, A/D, placement, fault injection, sensor panel | 2 |
| 3 | Dead reckoning, gyro/compass correction, occupancy grid | 2 |
| 4 | Subsumption behaviours, frontier and DFS exploration, A*, return home | 2 |
| 5 | AI terrain classifier, environment configurations, experiments, report | 1 + all |

Each stage must run before the next one starts; the interface and the three environments are completed together in the final stage.
