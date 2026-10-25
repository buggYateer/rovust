"""Pygame application: start menu, About page, and the live simulator."""
from __future__ import annotations

import math
from collections import deque

import numpy as np
import pygame

from ..ai.brain import AIBrain
from ..mission import Mission
from ..sensors.base import FAULT_MODES
from . import theme as T
from .render import (MapView, belief_rgb, camera_surface, draw_cell_path, draw_frontiers, draw_path,
                     draw_robot, draw_sensor_rays, world_rgb)
from .widgets import Button, OptionGroup, Toggle

W, H = 1380, 860


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(T.PROJECT_TITLE)
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self.screen_name = "menu"
        self.env = "cave"
        self.strategy = "frontier"
        self.localisation = "fused"
        self.use_ai = True
        self.seed = 1
        self.running = True
        self._build_menu()
        self._build_about()
        self.mission: Mission | None = None

    # =================================================================== MENU
    def _build_menu(self):
        self.menu_widgets = []
        cards_y = 190
        self.env_cards = []
        for i, env in enumerate(("cave", "mars", "underwater")):
            r = pygame.Rect(90 + i * 410, cards_y, 380, 230)
            self.env_cards.append((env, r))
        self.strategy_group = OptionGroup((90, 500, 580, 44), T.STRATEGIES, self.strategy,
                                          on_change=lambda k: setattr(self, "strategy", k))
        self.loc_group = OptionGroup((710, 500, 580, 44), T.LOCALISATION, self.localisation,
                                     on_change=lambda k: setattr(self, "localisation", k), size=14)
        self.ai_toggle = Toggle((90, 600, 280, 44), "AI terrain classifier + fault detection", self.use_ai,
                                on_change=lambda v: setattr(self, "use_ai", v))
        self.seed_minus = Button((400, 600, 44, 44), "-", on_click=lambda: self._seed(-1))
        self.seed_plus = Button((560, 600, 44, 44), "+", on_click=lambda: self._seed(+1))
        self.start_btn = Button((90, 700, 300, 56), "START MISSION", on_click=self.start_mission, size=20, accent=True)
        self.about_btn = Button((410, 700, 180, 56), "About", on_click=lambda: self._go("about"), size=18)
        self.quit_btn = Button((610, 700, 180, 56), "Quit", on_click=self.quit, size=18)
        self.menu_widgets = [self.strategy_group, self.loc_group, self.ai_toggle, self.seed_minus, self.seed_plus,
                             self.start_btn, self.about_btn, self.quit_btn]

    def _seed(self, d):
        self.seed = max(0, self.seed + d)

    def _go(self, name):
        self.screen_name = name

    def quit(self):
        self.running = False

    def draw_menu(self):
        s = self.screen
        s.fill(T.BG)
        T.text(s, T.PROJECT_TITLE, (W // 2, 60), 38, T.WHITE, bold=True, center=True)
        T.text(s, T.PROJECT_SUB, (W // 2, 104), 19, T.MUTED, center=True)
        T.text(s, f"{T.COURSE}  |  {T.DOCTOR}", (W // 2, 134), 15, T.MUTED, center=True)
        T.text(s, "1. Choose an environment", (90, 165), 16, T.ACCENT, bold=True)
        for env, r in self.env_cards:
            sel = env == self.env
            T.rounded(s, r, T.PANEL_LIGHT if sel else T.PANEL, 12, T.ACCENT if sel else T.BORDER, 2 if sel else 1)
            pygame.draw.rect(s, T.ENV_COLORS[env], (r.x, r.y, r.w, 10), border_top_left_radius=12, border_top_right_radius=12)
            T.text(s, T.ENV_TITLES[env], (r.x + 18, r.y + 24), 24, T.WHITE, bold=True)
            for i, line in enumerate(T.ENV_BLURB[env].split("\n")):
                T.text(s, line, (r.x + 18, r.y + 66 + i * 21), 14, T.TEXT if sel else T.MUTED)
            T.text(s, "SELECTED" if sel else "click to select", (r.x + 18, r.y + r.h - 32), 13,
                   T.ACCENT if sel else T.MUTED, bold=sel)
        T.text(s, "2. Exploration strategy", (90, 472), 16, T.ACCENT, bold=True)
        T.text(s, "3. Localisation used by the robot", (710, 472), 16, T.ACCENT, bold=True)
        T.text(s, "4. Options", (90, 572), 16, T.ACCENT, bold=True)
        T.text(s, f"seed  {self.seed}", (502, 622), 18, T.TEXT, center=True)
        T.text(s, "The seed changes the generated map and the sensor noise.", (620, 614), 14, T.MUTED)
        for wdg in self.menu_widgets:
            wdg.draw(s)
        T.text(s, "In the simulator:  SPACE pause   1-4 speed   L/S/I/T/V/F layers   click a sensor to inject a fault   ESC menu",
               (W // 2, H - 30), 14, T.MUTED, center=True)

    def handle_menu(self, event):
        for wdg in self.menu_widgets:
            if wdg.handle(event):
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for env, r in self.env_cards:
                if r.collidepoint(event.pos):
                    self.env = env
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.start_mission()
            elif event.key == pygame.K_ESCAPE:
                self.quit()

    # ================================================================== ABOUT
    def _build_about(self):
        self.about_back = Button((W // 2 - 90, H - 80, 180, 48), "Back", on_click=lambda: self._go("menu"), size=18)

    def draw_about(self):
        s = self.screen
        s.fill(T.BG)
        T.text(s, "About the project", (W // 2, 50), 34, T.WHITE, bold=True, center=True)
        left = pygame.Rect(70, 100, 640, 640)
        right = pygame.Rect(740, 100, 570, 640)
        T.rounded(s, left, T.PANEL, 14, T.BORDER)
        T.rounded(s, right, T.PANEL, 14, T.BORDER)
        T.text(s, T.PROJECT_TITLE, (left.x + 24, left.y + 22), 20, T.ACCENT, bold=True)
        lines = [
            "One exploration robot, three unknown environments. The rover is",
            "simulated from the bottom up, following the Robotics course:",
            "",
            "- Actuators: two DC motors driven by an H-bridge with PWM; the",
            "  duty-cycle -> speed curve is non-linear and calibrated.",
            "- Control: incremental shaft encoders feed a discrete PID velocity",
            "  loop per wheel; an I-controller on the encoder difference keeps",
            "  the differential drive straight.",
            "- Sensors: sonar ring (cone, specular loss, cross-talk), IR PSDs",
            "  with lookup-table calibration, cliff switches front and rear,",
            "  bumpers, compass / sun sensor, gyro + accelerometer, camera,",
            "  optical flow / DVL, battery, gas, light, pressure. All through",
            "  a modelled A/D converter, all faultable at run time.",
            "- Localisation: dead reckoning corrected by gyro and compass.",
            "- Mapping: log-odds occupancy grid + terrain and hazard layers.",
            "- Behaviour: subsumption - escape > cliff > avoid > home > explore.",
            "- Planning: frontier vs DFS exploration, A* on a cost map.",
            "- AI: Random-Forest terrain classifier on camera patches feeds",
            "  the planner's cost map; sensor fault detector; utility-based",
            "  frontier selection.",
            "",
            "Built in Python with Pygame, NumPy, SciPy and scikit-learn.",
        ]
        for i, line in enumerate(lines):
            T.text(s, line, (left.x + 24, left.y + 60 + i * 24), 15, T.TEXT if line.startswith("-") or not line.startswith(" ") else T.MUTED)
        T.text(s, T.COURSE, (right.x + 24, right.y + 22), 20, T.ACCENT, bold=True)
        T.text(s, "Supervisor", (right.x + 24, right.y + 64), 14, T.MUTED)
        T.text(s, T.DOCTOR, (right.x + 24, right.y + 84), 18, T.WHITE, bold=True)
        T.text(s, "Team", (right.x + 24, right.y + 134), 14, T.MUTED)
        for i, name in enumerate(T.TEAM):
            T.text(s, f"{i + 1}.  {name}", (right.x + 24, right.y + 158 + i * 30), 17, T.TEXT)
        T.text(s, "Faculty of Computers & Informatics - Zagazig University", (right.x + 24, right.y + 470), 14, T.MUTED)
        T.text(s, "Source: github.com/buggYateer/robotics-project", (right.x + 24, right.y + 494), 14, T.MUTED)
        self.about_back.draw(s)

    def handle_about(self, event):
        self.about_back.handle(event)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self._go("menu")

    # ============================================================== SIMULATOR
    def start_mission(self):
        ai = AIBrain() if self.use_ai else None
        self.mission = Mission(self.env, self.strategy, seed=self.seed, localisation=self.localisation, ai=ai)
        if ai is not None:
            ai.attach(self.mission)
        self.paused = False
        self.speed = 1
        self.layers = {"sonar": True, "ir": True, "terrain": True, "visited": False, "frontiers": True, "true_path": True}
        m = self.mission
        self.view_world = MapView(pygame.Rect(20, 60, 560, 420), m.world)
        self.view_belief = MapView(pygame.Rect(600, 60, 560, 420), m.world)
        self.world_surface = self.view_world.cells_to_surface(world_rgb(m.world, m.cfg.ambient_light))
        self.pid_hist = deque(maxlen=200)
        self.sensor_rects = {}
        self.sim_buttons = [
            Button((1180, 60, 180, 40), "Menu  (Esc)", on_click=lambda: self._go("menu")),
            Button((1180, 108, 180, 40), "Pause  (Space)", on_click=self._toggle_pause),
            Button((1180, 156, 85, 40), "x1", on_click=lambda: self._set_speed(1)),
            Button((1275, 156, 85, 40), "x4", on_click=lambda: self._set_speed(4)),
            Button((1180, 204, 85, 40), "x8", on_click=lambda: self._set_speed(8)),
            Button((1275, 204, 85, 40), "x16", on_click=lambda: self._set_speed(16)),
            Button((1180, 252, 180, 40), "Restart", on_click=self.start_mission),
        ]
        self._go("sim")

    def _toggle_pause(self):
        self.paused = not self.paused

    def _set_speed(self, v):
        self.speed = v

    def handle_sim(self, event):
        for b in self.sim_buttons:
            if b.handle(event):
                return
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k == pygame.K_ESCAPE:
                self._go("menu")
            elif k == pygame.K_SPACE:
                self._toggle_pause()
            elif k in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                self.speed = {pygame.K_1: 1, pygame.K_2: 4, pygame.K_3: 8, pygame.K_4: 16}[k]
            elif k == pygame.K_s:
                self.layers["sonar"] = not self.layers["sonar"]
            elif k == pygame.K_i:
                self.layers["ir"] = not self.layers["ir"]
            elif k == pygame.K_t:
                self.layers["terrain"] = not self.layers["terrain"]
            elif k == pygame.K_v:
                self.layers["visited"] = not self.layers["visited"]
            elif k == pygame.K_f:
                self.layers["frontiers"] = not self.layers["frontiers"]
            elif k == pygame.K_l:
                self.layers["true_path"] = not self.layers["true_path"]
            elif k == pygame.K_h:
                self.mission.robot.headlights = not self.mission.robot.headlights
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, r in self.sensor_rects.items():
                if r.collidepoint(event.pos):
                    s = self.mission.robot.sensors.by_name[name]
                    s.set_fault(FAULT_MODES[(FAULT_MODES.index(s.fault) + 1) % len(FAULT_MODES)])
                    if s.fault == "ok":
                        s.healthy = True

    def update_sim(self):
        m = self.mission
        if self.paused or m.done:
            return
        for _ in range(self.speed):
            m.step()
            d = m.robot.drive
            self.pid_hist.append((d.des_wl, d.meas_wl, d.des_wr, d.meas_wr, d.left.duty, d.right.duty))
            if m.done:
                break

    def draw_sim(self):
        s = self.screen
        m = self.mission
        s.fill(T.BG)
        status_col = {"exploring": T.GOOD, "returning": T.WARN, "returned": T.ACCENT, "fell": T.BAD, "battery_dead": T.BAD}.get(m.status, T.MUTED)
        T.text(s, f"{T.ENV_TITLES[m.cfg.name]}   |   {m.explorer.name}   |   {m.estimator.mode}", (20, 8), 20, T.WHITE, bold=True)
        T.text(s, f"t = {m.time:6.1f} s    x{self.speed}{'   PAUSED' if self.paused else ''}", (600, 12), 16, T.MUTED)
        T.text(s, m.status.upper() + (f"  ({m.stats['return_reason']})" if m.stats['return_reason'] else ""), (900, 12), 16, status_col, bold=True)

        # ---- true world
        vw = self.view_world
        T.rounded(s, vw.rect.inflate(8, 8), T.PANEL, 8, T.BORDER)
        s.blit(self.world_surface, vw.origin)
        T.text(s, "TRUE WORLD  (the robot never sees this)", (vw.rect.x + 4, vw.rect.y - 20), 13, T.MUTED)
        if self.layers["true_path"]:
            draw_path(s, vw, m.true_path, (255, 240, 120), 2)
        draw_sensor_rays(s, vw, m.robot, self.layers["sonar"], self.layers["ir"])
        draw_robot(s, vw, m.robot.pose, m.robot.radius)

        # ---- belief map
        vb = self.view_belief
        T.rounded(s, vb.rect.inflate(8, 8), T.PANEL, 8, T.BORDER)
        vb.blit_cells(s, belief_rgb(m.grid, self.layers["terrain"], True, self.layers["visited"]))
        T.text(s, "ROBOT'S MAP  (occupancy grid + terrain + hazards)", (vb.rect.x + 4, vb.rect.y - 20), 13, T.MUTED)
        if self.layers["frontiers"]:
            draw_frontiers(s, vb, m.grid, m.explorer.frontiers, m.explorer.target)
        draw_cell_path(s, vb, m.grid, m.explorer.path, (90, 220, 255))
        draw_path(s, vb, m.odom_path, (255, 110, 110), 1)
        draw_path(s, vb, m.est_path, (120, 255, 150), 2)
        draw_robot(s, vb, m.estimator.pose, m.robot.radius, T.GOOD)
        draw_robot(s, vb, m.estimator.odom, m.robot.radius * 0.6, (255, 110, 110), (255, 110, 110))
        hx, hy = vb.to_px(*m.grid.to_world(*m.home_cell))
        pygame.draw.circle(s, T.WHITE, (hx, hy), 5, 1)

        for b in self.sim_buttons:
            b.draw(s)
        self._draw_legend(pygame.Rect(1180, 300, 180, 180))
        self._draw_sensors(pygame.Rect(20, 500, 520, 340))
        self._draw_control(pygame.Rect(560, 500, 380, 340))
        self._draw_stats(pygame.Rect(960, 500, 400, 340))

    def _draw_legend(self, r):
        s = self.screen
        T.rounded(s, r, T.PANEL, 8, T.BORDER)
        T.text(s, "Legend", (r.x + 10, r.y + 8), 14, T.ACCENT, bold=True)
        items = [((255, 240, 120), "true path"), ((120, 255, 150), "fused estimate"), ((255, 110, 110), "encoders only"),
                 ((90, 220, 255), "planned path"), ((255, 220, 90), "frontiers / target"), ((230, 60, 60), "hazard (cliff/gas)"),
                 ((120, 200, 255), "sonar echo"), ((255, 120, 120), "IR beam")]
        for i, (c, label) in enumerate(items):
            pygame.draw.rect(s, c, (r.x + 12, r.y + 34 + i * 18, 12, 10))
            T.text(s, label, (r.x + 30, r.y + 30 + i * 18), 13, T.TEXT)

    def _draw_sensors(self, r):
        s = self.screen
        m = self.mission
        T.rounded(s, r, T.PANEL, 8, T.BORDER)
        T.text(s, "Sensors  (click a row to cycle: ok > stuck > dead > noisy)", (r.x + 10, r.y + 8), 14, T.ACCENT, bold=True)
        self.sensor_rects = {}
        sensors = m.robot.sensors.sensors
        cols = 2
        rows = math.ceil(len(sensors) / cols)
        col_w = (r.w - 20) // cols
        row_h = 17
        for i, sn in enumerate(sensors):
            cx = r.x + 10 + (i // rows) * col_w
            cy = r.y + 32 + (i % rows) * row_h
            rect = pygame.Rect(cx, cy, col_w - 6, row_h)
            self.sensor_rects[sn.name] = rect
            if not sn.healthy:
                col = T.BAD
            elif sn.fault != "ok":
                col = T.WARN
            else:
                col = T.TEXT
            if rect.collidepoint(pygame.mouse.get_pos()):
                pygame.draw.rect(s, T.PANEL_LIGHT, rect, border_radius=4)
            unit = sn.units
            if sn.cls.signal == "binary":
                val = "ON" if sn.value > 0.5 else "off"
            elif sn.name == "camera":
                val = f"{m.ai.last[0]} {m.ai.last[1]:.0%}" if m.ai is not None else f"{sn.value:.2f}"
            else:
                val = f"{sn.value:7.3f}{unit}"
            tag = "" if sn.fault == "ok" else f" [{sn.fault}]"
            T.text(s, f"{sn.name:9}", (cx + 2, cy + 1), 13, col)
            T.text(s, val + tag, (cx + 78, cy + 1), 13, col)
            # a small bar for ranging sensors
            mx = getattr(sn, "max_range", None)
            if mx and sn.cls.signal != "binary":
                frac = min(1.0, sn.value / mx)
                pygame.draw.rect(s, T.BORDER, (cx + col_w - 70, cy + 5, 60, 7))
                pygame.draw.rect(s, (120, 200, 255) if sn.healthy else T.BAD, (cx + col_w - 70, cy + 5, int(60 * frac), 7))
        cam = m.robot.sensors.camera
        if cam is not None:
            img = camera_surface(cam.image, 64)
            s.blit(img, (r.right - 76, r.bottom - 76))
            pygame.draw.rect(s, T.BORDER, (r.right - 76, r.bottom - 76, 64, 64), 1)
            T.text(s, "camera", (r.right - 76, r.bottom - 92), 12, T.MUTED)
        if m.ai is not None and m.ai.detector is not None and m.ai.detector.alarms:
            name, verdict = m.ai.detector.alarms[-1]
            T.text(s, f"AI fault detector: {name} looks {verdict} -> ignored", (r.x + 10, r.bottom - 22), 13, T.BAD)

    def _draw_control(self, r):
        s = self.screen
        m = self.mission
        d = m.robot.drive
        T.rounded(s, r, T.PANEL, 8, T.BORDER)
        T.text(s, "Motor control  (PWM > DC motor > encoder > PID)", (r.x + 10, r.y + 8), 14, T.ACCENT, bold=True)
        T.text(s, f"behaviour: {m.arbiter.active_name}", (r.x + 10, r.y + 30), 15, T.ACCENT2, bold=True)
        T.text(s, f"cmd v={m.cmd[0]:+.2f} m/s  w={m.cmd[1]:+.2f} rad/s", (r.x + 190, r.y + 31), 13, T.MUTED)
        T.text(s, f"L: duty {d.left.duty:+.2f}  enc {d.enc_l.count:7d}  want {d.des_wl:5.1f}  meas {d.meas_wl:5.1f} rad/s  {d.left.bridge.state}",
               (r.x + 10, r.y + 54), 13, T.TEXT)
        T.text(s, f"R: duty {d.right.duty:+.2f}  enc {d.enc_r.count:7d}  want {d.des_wr:5.1f}  meas {d.meas_wr:5.1f} rad/s  {d.right.bridge.state}",
               (r.x + 10, r.y + 72), 13, T.TEXT)
        T.text(s, f"slip L {d.slip_l:.2f}  R {d.slip_r:.2f}    straight-drive I-term {d.straight.sum * d.straight.ki:+.3f}",
               (r.x + 10, r.y + 90), 13, T.MUTED)
        # plot: desired vs measured left wheel speed and duty
        plot = pygame.Rect(r.x + 10, r.y + 115, r.w - 20, r.h - 125)
        pygame.draw.rect(s, T.BG, plot)
        pygame.draw.rect(s, T.BORDER, plot, 1)
        if len(self.pid_hist) > 2:
            h = list(self.pid_hist)
            n = len(h)
            vmax = m.cfg.drive.max_wheel_speed

            def line(idx, color, scale, offset=0.5):
                pts = [(plot.x + i * plot.w / (self.pid_hist.maxlen - 1),
                        plot.centery - (h[i][idx] / scale) * (plot.h / 2 - 4) * (1 if offset else 1))
                       for i in range(n)]
                if len(pts) > 1:
                    pygame.draw.lines(s, color, False, pts, 1)
            pygame.draw.line(s, T.BORDER, (plot.x, plot.centery), (plot.right, plot.centery), 1)
            line(0, T.ACCENT2, vmax)
            line(1, T.GOOD, vmax)
            line(4, (255, 110, 110), 1.0)
        T.text(s, "left wheel:  desired", (plot.x + 6, plot.y + 4), 12, T.ACCENT2)
        T.text(s, "measured (encoder)", (plot.x + 130, plot.y + 4), 12, T.GOOD)
        T.text(s, "PWM duty", (plot.x + 260, plot.y + 4), 12, (255, 110, 110))

    def _draw_stats(self, r):
        s = self.screen
        m = self.mission
        T.rounded(s, r, T.PANEL, 8, T.BORDER)
        T.text(s, "Mission statistics", (r.x + 10, r.y + 8), 14, T.ACCENT, bold=True)
        cov = m.coverage()
        bat = m.robot.battery
        rows = [
            ("coverage of reachable area", f"{cov:6.1%}"),
            ("mapped cells", f"{m.grid.known_count():d}"),
            ("path length", f"{m.robot.distance:6.1f} m"),
            ("steps / time", f"{m.step_count:d} / {m.time:.0f} s"),
            ("backtracking events", f"{m.explorer.backtracks:d}"),
            ("collisions / bumper events", f"{m.robot.collisions:d} / {m.stats['bumps']:d}"),
            ("cliff events", f"{m.stats['cliff_events']:d}"),
            ("localisation error (used)", f"{m.estimator.error():.2f} m"),
            ("  encoders-only error", f"{m.estimator.odom.distance_to(m.robot.pose):.2f} m"),
            ("battery", f"{bat.fraction:5.0%}  {bat.voltage:.1f} V  {bat.power:.1f} W"),
            ("frontiers known", f"{len(m.explorer.frontiers):d}"),
        ]
        if m.ai is not None and m.ai.terrain is not None:
            rows.append(("AI terrain accuracy (live)", f"{m.ai.terrain_accuracy_live:5.1%}  ({m.ai.terrain.predictions} frames)"))
        for i, (k, v) in enumerate(rows):
            T.text(s, k, (r.x + 12, r.y + 34 + i * 22), 14, T.MUTED)
            T.text(s, v, (r.right - 12, r.y + 34 + i * 22), 14, T.TEXT, right=True)
        # coverage bar
        bar = pygame.Rect(r.x + 12, r.bottom - 26, r.w - 24, 12)
        pygame.draw.rect(s, T.BORDER, bar, border_radius=6)
        pygame.draw.rect(s, T.GOOD, (bar.x, bar.y, int(bar.w * cov), bar.h), border_radius=6)

    # ==================================================================== LOOP
    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif self.screen_name == "menu":
                    self.handle_menu(event)
                elif self.screen_name == "about":
                    self.handle_about(event)
                else:
                    self.handle_sim(event)
            if self.screen_name == "menu":
                self.draw_menu()
            elif self.screen_name == "about":
                self.draw_about()
            else:
                self.update_sim()
                self.draw_sim()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()
