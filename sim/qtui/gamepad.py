"""Game controller input for the desktop (USB dongle or Bluetooth).

Qt 6 has no gamepad module, so the controller is read through SDL2 via
pygame-ce, polled from a Qt timer. pygame-ce is optional: without it the
rest of the program works and the setup panel says how to enable it.

Mapping, like a driving game (the same as the phone console; PlayStation names
first, Xbox names in brackets):
    ✕ (A) held            gas: drive forward; the left stick or the arrows steer
    △ (Y) held            reverse; the left stick or the arrows steer
    left stick / arrows   alone: point-to-go, push where the rover should go on
                          the map (circle the stick to spin it in place)
    R2 / L2 + right stick analog throttle forward / reverse, steer
    Start  stop     ○ (B)  headlights     □ (X)  return home     L1 / R1  mode
"""
from __future__ import annotations

import os

from PySide6.QtCore import QObject, QTimer, Signal

DEADZONE = 0.15

# Layouts SDL does not know out of the box. "Twin USB Joystick" is the common
# PlayStation-2-to-USB adapter (two pads on one dongle): without this its
# buttons arrive as bare numbers in a different order (A would be Triangle).
EXTRA_MAPPINGS = [
    "03000000632500005505000000000000,Twin USB Joystick,a:b2,b:b1,back:b8,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,"
    "dpup:h0.1,leftshoulder:b6,leftstick:b10,lefttrigger:b4,leftx:a0,lefty:a1,rightshoulder:b7,rightstick:b11,"
    "righttrigger:b5,rightx:a3,righty:a2,start:b9,x:b3,y:b0,platform:Windows,",
]
PLAYSTATION_HINTS = ("twin usb", "playstation", "dualshock", "dualsense", "ps2", "ps3", "ps4", "ps5", "sony")


def is_playstation(name: str) -> bool:
    n = (name or "").lower()
    return any(h in n for h in PLAYSTATION_HINTS)


def _dz(v: float) -> float:
    if abs(v) < DEADZONE:
        return 0.0
    return (v - DEADZONE * (1 if v > 0 else -1)) / (1 - DEADZONE)


class Gamepad(QObject):
    """Emits ``steer(x, y)`` (point-to-go, map frame) or ``drive(forward, turn)``
    (car-style triggers) while a control is off-centre, one zero when it
    returns, ``button(name)`` on presses, ``connected(name)`` and
    ``disconnected()``."""
    steer = Signal(float, float)
    drive = Signal(float, float)
    button = Signal(str)
    live = Signal(float, float, str)     # stick x, y and the buttons held now: for the on-screen view
    connected = Signal(str)
    disconnected = Signal()

    BUTTONS = ("b", "x", "start", "leftshoulder", "rightshoulder")      # one-shot actions

    def __init__(self, parent=None, interval_ms: int = 33):
        super().__init__(parent)
        self.available = False
        self.pad = None
        self.name = ""
        self._prev = {}
        self._moving = False
        try:
            os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")   # keep reading while Qt has the focus
            os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")                     # SDL needs a video system for events, not a window
            known = os.environ.get("SDL_GAMECONTROLLERCONFIG", "")
            os.environ["SDL_GAMECONTROLLERCONFIG"] = chr(10).join([m for m in EXTRA_MAPPINGS if m.split(",")[0] not in known] + ([known] if known else []))
            import pygame
            from pygame._sdl2 import controller
            pygame.display.init()
            pygame.joystick.init()
            controller.init()
            self._pg, self._ctl = pygame, controller
            self.available = True
        except Exception:
            return
        self.timer = QTimer(self)
        self.timer.setInterval(interval_ms)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        QTimer.singleShot(0, self._find)

    # ----------------------------------------------------------------- devices
    def _find(self):
        if self.pad is not None:
            return
        for i in range(self._pg.joystick.get_count()):
            try:
                if self._ctl.is_controller(i):
                    self.pad = self._ctl.Controller(i)
                    self.name = self.pad.name or "Gamepad"
                else:
                    js = self._pg.joystick.Joystick(i)
                    self.pad = js
                    self.name = js.get_name() or "Gamepad"
                self._prev = {}
                self.connected.emit(self.name)
                return
            except Exception:
                continue

    def _lost(self):
        self.pad = None
        self.name = ""
        if self._moving:
            self._moving = False
            self.steer.emit(0.0, 0.0)
        self.disconnected.emit()

    # -------------------------------------------------------------------- poll
    def poll(self):
        pg = self._pg
        try:
            for e in pg.event.get():
                if e.type in (pg.JOYDEVICEADDED, getattr(pg, "CONTROLLERDEVICEADDED", -1)):
                    self._find()
                elif e.type in (pg.JOYDEVICEREMOVED, getattr(pg, "CONTROLLERDEVICEREMOVED", -1)):
                    if self.pad is not None and not self._attached():
                        self._lost()
                        self._find()
        except Exception:
            return
        if self.pad is None:
            return
        try:
            (sx, sy), (fwd, turn), pressed = self._read()
        except Exception:
            self._lost()
            return
        for b in self.BUTTONS:
            if pressed.get(b) and not self._prev.get(b):
                self.button.emit(b)
        if pressed != self._prev or (sx, sy) != getattr(self, "_last_stick", None):
            self._last_stick = (sx, sy)
            held = " ".join(k for k, v in pressed.items() if v)
            if fwd > 0.05:
                held += " RT"
            elif fwd < -0.05:
                held += " LT"
            self.live.emit(sx, sy, held.strip())
        self._prev = pressed
        if sx or sy:
            self._moving = True
            self.steer.emit(sx, sy)
        elif fwd or turn:
            self._moving = True
            self.drive.emit(fwd, turn)
        elif self._moving:
            self._moving = False
            self.steer.emit(0.0, 0.0)

    def _attached(self) -> bool:
        try:
            return bool(self.pad.attached()) if hasattr(self.pad, "attached") else bool(self.pad.get_init())
        except Exception:
            return False

    def _read(self):
        """((steer x, steer y), (forward, turn), pressed buttons).
        steer: left stick / d-pad, x right, y up (map frame), each in [-1, 1].
        forward/turn: triggers + right stick, turn positive = left."""
        p, c, pg = self.pad, self._ctl, self._pg
        if isinstance(p, c.Controller):
            ax = lambda k: p.get_axis(k) / 32767.0
            x, y = _dz(ax(pg.CONTROLLER_AXIS_LEFTX)), _dz(ax(pg.CONTROLLER_AXIS_LEFTY))
            rx = _dz(ax(pg.CONTROLLER_AXIS_RIGHTX))
            rt, lt = ax(pg.CONTROLLER_AXIS_TRIGGERRIGHT), ax(pg.CONTROLLER_AXIS_TRIGGERLEFT)
            btn = lambda k: bool(p.get_button(k))
            pressed = {"a": btn(pg.CONTROLLER_BUTTON_A), "b": btn(pg.CONTROLLER_BUTTON_B), "x": btn(pg.CONTROLLER_BUTTON_X),
                       "y": btn(pg.CONTROLLER_BUTTON_Y), "start": btn(pg.CONTROLLER_BUTTON_START),
                       "leftshoulder": btn(pg.CONTROLLER_BUTTON_LEFTSHOULDER), "rightshoulder": btn(pg.CONTROLLER_BUTTON_RIGHTSHOULDER)}
            up, down = btn(pg.CONTROLLER_BUTTON_DPAD_UP), btn(pg.CONTROLLER_BUTTON_DPAD_DOWN)
            left, right = btn(pg.CONTROLLER_BUTTON_DPAD_LEFT), btn(pg.CONTROLLER_BUTTON_DPAD_RIGHT)
        else:                                    # unknown joystick: plain axes, buttons 0..5, first hat
            n = p.get_numaxes()
            x = _dz(p.get_axis(0)) if n > 0 else 0.0
            y = _dz(p.get_axis(1)) if n > 1 else 0.0
            rx = _dz(p.get_axis(2)) if n > 2 else 0.0
            rt = lt = 0.0
            nb = p.get_numbuttons()
            btn = lambda i: bool(p.get_button(i)) if i < nb else False
            pressed = {"a": btn(0), "b": btn(1), "x": btn(2), "y": btn(3), "start": btn(9),
                       "leftshoulder": btn(4), "rightshoulder": btn(5)}
            hx, hy = p.get_hat(0) if p.get_numhats() else (0, 0)
            up, down, left, right = hy > 0, hy < 0, hx < 0, hx > 0
        sx, sy = x, -y                            # stick up = map up
        if up or down or left or right:
            sx = (1.0 if right else 0.0) - (1.0 if left else 0.0)
            sy = (1.0 if up else 0.0) - (1.0 if down else 0.0)
        fwd = (rt - lt) if (rt > 0.05 or lt > 0.05) else 0.0
        turn = -rx * 0.8
        gas, back = pressed["a"], pressed["y"]
        if gas != back:
            # driving-game style: ✕ / △ is the pedal, the stick or the arrows steer
            fwd = 1.0 if gas else -1.0
            turn = -sx * 0.8
            sx = sy = 0.0
        clamp = lambda v: max(-1.0, min(1.0, v))
        return (clamp(sx), clamp(sy)), (clamp(fwd), clamp(turn)), pressed
