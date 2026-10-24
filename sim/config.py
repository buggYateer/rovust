"""Environment configurations.

Everything that differs between the cave, Mars and the underwater site lives
here. The robot's control, estimation and decision code never changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MotorConfig:
    vcc: float = 12.0            # H-bridge supply voltage [V]
    kv: float = 25.0             # no-load speed constant [rad/s per V] (motor shaft)
    tau: float = 0.15            # mechanical time constant [s]
    gear_ratio: float = 30.0     # motor revs per wheel rev
    deadband: float = 0.06       # duty below which static friction wins
    duty_exponent: float = 1.3   # non-linear duty -> effective voltage curve
    encoder_ticks: int = 16      # ticks per motor-shaft revolution (before gearbox)
    mismatch: float = 0.04       # +/- fractional difference between the two motors


@dataclass
class PIDConfig:
    kp: float = 0.08
    ki: float = 0.6
    kd: float = 0.002


@dataclass
class DriveConfig:
    kind: str = "wheels"         # "wheels" | "thrusters"
    wheel_radius: float = 0.05   # [m]
    wheel_base: float = 0.30     # distance between the two wheels [m]
    robot_radius: float = 0.20   # body radius used for collisions [m]
    max_wheel_speed: float = 12.0  # [rad/s] at the wheel
    slip_noise: float = 0.03     # random slip std (fraction)


@dataclass
class SensorConfig:
    """Which sensors are mounted and their physical parameters."""
    sonar_count: int = 8
    sonar_range: float = 4.0        # [m]
    sonar_cone_deg: float = 15.0
    sonar_noise: float = 0.03       # std as fraction of range
    sonar_crosstalk: float = 0.005  # probability a reading comes from a neighbour's echo
    sonar_specular_deg: float = 65.0  # incidence angle beyond which the echo is lost (rough walls: larger)
    ir_count: int = 3
    ir_range: float = 0.8           # [m] Sharp GP2D12-like
    ir_min_range: float = 0.06      # below this the reading is wrong (lecture)
    ir_noise: float = 0.02
    cliff_sensors: bool = True
    cliff_lookahead: float = 0.12   # [m] ahead of the front corners
    bumpers: bool = True
    compass: bool = True
    compass_noise_deg: float = 2.0
    compass_disturbance: float = 0.0  # local magnetic disturbance amplitude [rad]
    sun_sensor: bool = False        # absolute heading from the sun (Mars: no magnetic field)
    sun_noise_deg: float = 3.0
    imu: bool = True
    gyro_noise: float = 0.01        # [rad/s]
    gyro_bias: float = 0.004        # [rad/s] constant bias (drift source)
    camera: bool = True
    camera_range: float = 1.0       # [m] ahead of the robot
    light_sensor: bool = False
    gas_sensor: bool = False
    pressure_sensor: bool = False
    dvl: bool = False               # Doppler velocity log (underwater odometry)
    optical_flow: bool = False      # downward optical-flow sensor: ground speed immune to wheel slip
    adc_bits: int = 10
    adc_vref: float = 5.0


@dataclass
class EnvConfig:
    name: str
    description: str
    width: int = 80                 # cells
    height: int = 60                # cells
    cell_size: float = 0.2          # [m]
    seed: int = 0
    ambient_light: float = 1.0      # 0 = darkness
    water_current: tuple = (0.0, 0.0)   # [m/s] constant drift applied to the body
    current_noise: float = 0.0
    battery_wh: float = 20.0
    battery_idle_w: float = 1.5
    headlight_w: float = 4.0
    motor: MotorConfig = field(default_factory=MotorConfig)
    pid: PIDConfig = field(default_factory=PIDConfig)
    drive: DriveConfig = field(default_factory=DriveConfig)
    sensors: SensorConfig = field(default_factory=SensorConfig)
    colors: dict = field(default_factory=dict)


def cave() -> EnvConfig:
    return EnvConfig(
        name="cave",
        description="Narrow branching corridors, dead ends, darkness, gas pockets.",
        width=72, height=52, cell_size=0.2,
        ambient_light=0.05,
        battery_wh=18.0,
        sensors=SensorConfig(
            sonar_count=8, sonar_range=2.5, sonar_cone_deg=15.0, sonar_noise=0.04, sonar_specular_deg=72.0,
            ir_count=3, cliff_sensors=True, bumpers=True,
            compass=True, compass_noise_deg=4.0, compass_disturbance=0.08,
            imu=True, camera=True, camera_range=0.6,
            light_sensor=True, gas_sensor=True, optical_flow=True,
        ),
    )


def mars() -> EnvConfig:
    return EnvConfig(
        name="mars",
        description="Open terrain with rocks, craters and sandy ground with high wheel slip.",
        width=100, height=72, cell_size=0.2,
        ambient_light=0.9,
        battery_wh=25.0,
        drive=DriveConfig(slip_noise=0.06),
        sensors=SensorConfig(
            sonar_count=8, sonar_range=5.0, sonar_cone_deg=15.0, sonar_noise=0.02,
            ir_count=3, cliff_sensors=True, bumpers=True,
            compass=False,          # Mars has no usable global magnetic field
            sun_sensor=True,
            imu=True, gyro_bias=0.006, camera=True, camera_range=1.2,
            optical_flow=True,
        ),
    )


def underwater() -> EnvConfig:
    return EnvConfig(
        name="underwater",
        description="Flooded site: reef walls, mud, a water current, sonar instead of light sensing.",
        width=90, height=64, cell_size=0.2,
        ambient_light=0.3,
        water_current=(0.04, -0.02), current_noise=0.02,
        battery_wh=22.0,
        drive=DriveConfig(kind="thrusters", slip_noise=0.08),
        sensors=SensorConfig(
            sonar_count=12, sonar_range=6.0, sonar_cone_deg=25.0, sonar_noise=0.05, sonar_specular_deg=78.0,
            sonar_crosstalk=0.01,
            ir_count=0, cliff_sensors=False, bumpers=True,
            compass=True, compass_noise_deg=3.0,
            imu=True, camera=True, camera_range=0.5,
            pressure_sensor=True, dvl=True,
        ),
    )


ENVIRONMENTS = {"cave": cave, "mars": mars, "underwater": underwater}


def get_env(name: str, seed: int = 0) -> EnvConfig:
    cfg = ENVIRONMENTS[name]()
    cfg.seed = seed
    return cfg
