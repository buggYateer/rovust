"""Tiny immediate-mode widgets: buttons, option groups, toggles."""
from __future__ import annotations

import pygame

from . import theme as T


class Button:
    def __init__(self, rect, label, on_click=None, color=T.PANEL_LIGHT, size=16, accent=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.color = color
        self.size = size
        self.accent = accent
        self.hover = False
        self.enabled = True

    def draw(self, surf):
        base = T.ACCENT if self.accent else self.color
        col = tuple(min(255, c + 22) for c in base) if self.hover and self.enabled else base
        if not self.enabled:
            col = T.PANEL
        T.rounded(surf, self.rect, col, 8, T.BORDER)
        T.text(surf, self.label, self.rect.center, self.size,
               T.BG if self.accent else (T.TEXT if self.enabled else T.MUTED), bold=self.accent, center=True)

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.enabled:
            if self.rect.collidepoint(event.pos) and self.on_click:
                self.on_click()
                return True
        return False


class OptionGroup:
    """One-of-N selector drawn as a row (or column) of pills."""

    def __init__(self, rect, options, value, on_change=None, vertical=False, size=15):
        self.rect = pygame.Rect(rect)
        self.options = options          # list of (key, label)
        self.value = value
        self.on_change = on_change
        self.vertical = vertical
        self.size = size
        self.buttons = []
        self._layout()

    def _layout(self):
        self.buttons = []
        n = len(self.options)
        gap = 6
        if self.vertical:
            h = (self.rect.h - gap * (n - 1)) // n
            for i, (k, label) in enumerate(self.options):
                r = pygame.Rect(self.rect.x, self.rect.y + i * (h + gap), self.rect.w, h)
                self.buttons.append((k, Button(r, label, size=self.size)))
        else:
            w = (self.rect.w - gap * (n - 1)) // n
            for i, (k, label) in enumerate(self.options):
                r = pygame.Rect(self.rect.x + i * (w + gap), self.rect.y, w, self.rect.h)
                self.buttons.append((k, Button(r, label, size=self.size)))

    def draw(self, surf):
        for k, b in self.buttons:
            b.accent = (k == self.value)
            b.draw(surf)

    def handle(self, event):
        for k, b in self.buttons:
            if event.type == pygame.MOUSEMOTION:
                b.hover = b.rect.collidepoint(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and b.rect.collidepoint(event.pos):
                if self.value != k:
                    self.value = k
                    if self.on_change:
                        self.on_change(k)
                return True
        return False


class Toggle(Button):
    def __init__(self, rect, label, value=False, on_change=None, size=15):
        super().__init__(rect, label, size=size)
        self.value = value
        self.on_change = on_change

    def draw(self, surf):
        self.accent = self.value
        super().draw(surf)

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.value = not self.value
            if self.on_change:
                self.on_change(self.value)
            return True
        return False
