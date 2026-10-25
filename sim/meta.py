"""Project constants shared by the desktop interface, the console and the reports."""

ROVER_NAME = "PyRov"           # the rover's name, shown in window titles and the console
PROJECT_TITLE = "Multi-Environment Autonomous Exploration Rover"
PROJECT_SUB = "A Python-based simulation - from motor control to mapping"
COURSE = "Robotics - Team Project"
DOCTOR = "Dr. Elshaimaa Nabil Nada"
TEAM = [
    "Ahmed Hamed Mohamed", "Aml Hesham Hosny", "Tassneem Amin Gamil",
    "Kholoud Waleed Attia", "Donia Essam Fathy", "Mazen Mohamed Hussien",
    "Mohamed Osama Salah", "Mohamed Elsayed Mohamed", "Mahmoud Ahmed Abdelghani",
]

ENV_COLORS = {"cave": (120, 92, 70), "mars": (200, 92, 60), "underwater": (40, 120, 190)}
ENV_TITLES = {"cave": "Cave", "mars": "Mars Surface", "underwater": "Underwater Site"}
ENV_BLURB = {
    "cave": "Narrow branching corridors, dead ends,\ndarkness, mud, pits and gas pockets.\n\n"
            "Short sonar range, headlights, compass\ndisturbed by iron in the rock.",
    "mars": "Open terrain with rock fields, craters and\nsandy ground with heavy wheel slip.\n\n"
            "No magnetic field: heading from a sun\nsensor; optical flow sees true ground speed.",
    "underwater": "Flooded site with reef walls, mud flats\nand a steady current.\n\n"
                  "Thrusters instead of wheels, sonar instead\nof light, DVL instead of encoders.",
}
STRATEGIES = [("frontier", "Nearest frontier"), ("dfs", "DFS + backtracking"), ("utility", "Utility (AI)")]
LOCALISATION = [("fused", "Fused (gyro+heading+flow)"), ("odometry", "Encoders only"), ("perfect", "Perfect (reference)")]
