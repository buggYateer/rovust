"""A large live view of one map, opened by clicking the map in the main window."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from .i18n import tr
from .mapview import MapWidget


class MapPopup(QDialog):
    def __init__(self, parent, title: str, mission, kind: str, layers: dict):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.setModal(False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        self.view = MapWidget(title)
        self.view.set_mission(mission, kind, layers)
        lay.addWidget(self.view, 1)
        hint = QLabel(tr("popupHint"))
        hint.setObjectName("hint")
        lay.addWidget(hint)
        pw = parent.width() if parent else 1200
        ph = parent.height() if parent else 800
        self.resize(int(pw * 0.8), int(ph * 0.8))

    def set_mission(self, mission, layers):
        self.view.set_mission(mission, self.view.kind, layers)

    def refresh(self):
        if self.isVisible():
            self.view.update()
