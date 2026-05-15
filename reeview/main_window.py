from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QTabWidget

from .config import Config
from .settings_tab import SettingsTab
from .view_tab import ViewTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ReeView")
        self.resize(1200, 800)

        self._config = Config.load()

        self._tabs = QTabWidget()
        self._view_tab = ViewTab(self._config)
        self._settings_tab = SettingsTab(self._config)
        self._settings_tab.config_changed.connect(self._view_tab.refresh_from_config)
        self._tabs.addTab(self._view_tab, "View")
        self._tabs.addTab(self._settings_tab, "Settings")
        self.setCentralWidget(self._tabs)

        self._install_shortcuts()
        self._restore_geometry()

    def _on_view_tab(self) -> bool:
        return self._tabs.currentWidget() is self._view_tab

    def _install_shortcuts(self) -> None:
        def add(seq, slot):
            sc = QShortcut(QKeySequence(seq), self)
            sc.activated.connect(slot)

        add(Qt.Key_Right, lambda: self._on_view_tab() and self._view_tab.next())
        add(Qt.Key_Left, lambda: self._on_view_tab() and self._view_tab.prev())
        add(Qt.Key_Space, lambda: self._on_view_tab() and self._view_tab.toggle_video_play())
        add("Ctrl+Z", lambda: self._on_view_tab() and self._view_tab.undo())
        add("Shift+Right", lambda: self._on_view_tab() and self._view_tab.skip_video(self._config.video_skip_seconds))
        add("Shift+Left", lambda: self._on_view_tab() and self._view_tab.skip_video(-self._config.video_skip_seconds))

        for i in range(9):
            def make_handler(idx: int):
                def handler() -> None:
                    if self._on_view_tab():
                        self._view_tab.move_to_destination(idx)
                return handler
            add(str(i + 1), make_handler(i))

    def _restore_geometry(self) -> None:
        if not self._config.window_geometry:
            return
        try:
            ba = QByteArray.fromBase64(self._config.window_geometry.encode("ascii"))
            self.restoreGeometry(ba)
        except Exception:
            pass

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt signature)
        geom = self.saveGeometry()
        self._config.window_geometry = bytes(geom.toBase64()).decode("ascii")
        self._config.save()
        super().closeEvent(event)
