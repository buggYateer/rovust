"""Colours, fonts and the team credits shown in the interface."""
import pygame

BG = (16, 18, 24)
PANEL = (26, 29, 38)
PANEL_LIGHT = (36, 40, 52)
BORDER = (58, 64, 80)
TEXT = (226, 228, 235)
MUTED = (140, 146, 160)
ACCENT = (86, 182, 255)
ACCENT2 = (255, 170, 60)
GOOD = (90, 210, 120)
WARN = (255, 200, 80)
BAD = (255, 90, 90)
WHITE = (255, 255, 255)

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

PROJECT_TITLE = "Multi-Environment Autonomous Exploration Rover"
PROJECT_SUB = "A Python-based simulation - from motor control to mapping"
COURSE = "Robotics - Team Project"
DOCTOR = "Dr. Elshaimaa Nabil Nada"
TEAM = [
    "Ahmed Hamed Mohamed", "Aml Hesham Hosny", "Tassneem Amin Gamil",
    "Kholoud Waleed Attia", "Donia Essam Fathy", "Mazen Mohamed Hussien",
    "Mohamed Osama Salah", "Mohamed Elsayed Mohamed", "Mahmoud Ahmed Abdelghani",
]

_fonts = {}


def font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _fonts:
        name = pygame.font.match_font("segoeui,dejavusans,arial", bold=bold)
        _fonts[key] = pygame.font.Font(name, size)
    return _fonts[key]


def text(surface, s, pos, size=16, color=TEXT, bold=False, center=False, right=False):
    img = font(size, bold).render(s, True, color)
    r = img.get_rect()
    if center:
        r.center = pos
    elif right:
        r.topright = pos
    else:
        r.topleft = pos
    surface.blit(img, r)
    return r


def rounded(surface, rect, color, radius=10, border=None, width=1):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surface, border, rect, width, border_radius=radius)
