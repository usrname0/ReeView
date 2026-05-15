from __future__ import annotations

from collections import deque
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .config import Config
from .file_manager import FileManager, Move
from .media_widget import MediaWidget


class ViewTab(QWidget):
    def __init__(self, config: Config, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._fm = FileManager()
        self._undo_stack: deque[Move] = deque()
        self._dest_buttons: list[QPushButton] = []

        root = QVBoxLayout(self)

        center_row = QHBoxLayout()
        self._media = MediaWidget()
        self._media.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._media.set_loop_enabled(self._config.loop_video)
        self._media.set_muted(self._config.muted)
        self._media.loop_toggled.connect(self._on_loop_toggled)
        self._media.mute_toggled.connect(self._on_mute_toggled)
        center_row.addWidget(self._media, 1)

        self._dest_column = QVBoxLayout()
        col_container = QWidget()
        col_container.setFixedWidth(220)
        col_container.setLayout(self._dest_column)
        center_row.addWidget(col_container)

        root.addLayout(center_row, 1)

        nav_row = QHBoxLayout()
        self._prev_btn = QPushButton("◀ Prev")
        self._prev_btn.clicked.connect(self.prev)
        self._next_btn = QPushButton("Next ▶")
        self._next_btn.clicked.connect(self.next)
        self._undo_btn = QPushButton("Undo")
        self._undo_btn.clicked.connect(self.undo)
        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignCenter)
        nav_row.addWidget(self._prev_btn)
        nav_row.addWidget(self._status, 1)
        nav_row.addWidget(self._undo_btn)
        nav_row.addWidget(self._next_btn)
        root.addLayout(nav_row)

        self.refresh_from_config()

    def refresh_from_config(self) -> None:
        src = self._config.source_folder
        self._fm.set_source(Path(src) if src else None)
        self._rebuild_destination_buttons()
        self._reload_current()

    def next(self) -> None:
        self._fm.next()
        self._reload_current()

    def prev(self) -> None:
        self._fm.prev()
        self._reload_current()

    def move_to_destination(self, index: int) -> None:
        if index < 0 or index >= len(self._config.destinations):
            return
        if self._fm.current() is None:
            return
        dest = Path(self._config.destinations[index].path)
        # QMediaPlayer keeps the video file open while it's the current source.
        # Drop the handle before moving, or Windows fails with WinError 32.
        was_video = self._media.is_video_active()
        if was_video:
            self._media.release_current()
        try:
            move = self._move_with_retry(dest)
        except OSError as e:
            self._status.setText(f"Move failed: {e}")
            if was_video:
                self._reload_current()
            return
        if move is None:
            return
        self._undo_stack.append(move)
        self._reload_current()

    def _move_with_retry(self, dest: Path):
        # WinMF closes the file asynchronously after setSource(QUrl()); pump
        # events between attempts so the OS releases the handle in time.
        last_err: OSError | None = None
        for _ in range(20):
            try:
                return self._fm.move_current_to(dest)
            except PermissionError as e:
                last_err = e
                QCoreApplication.processEvents()
        if last_err is not None:
            raise last_err
        return None

    def toggle_video_play(self) -> None:
        if self._media.is_video_active():
            self._media.toggle_play()

    def skip_video(self, seconds: float) -> None:
        self._media.skip(seconds)

    def _on_loop_toggled(self, enabled: bool) -> None:
        self._config.loop_video = enabled
        self._config.save()

    def _on_mute_toggled(self, muted: bool) -> None:
        self._config.muted = muted
        self._config.save()

    def undo(self) -> None:
        if not self._undo_stack:
            return
        move = self._undo_stack.pop()
        try:
            self._fm.undo(move)
        except OSError as e:
            self._status.setText(f"Undo failed: {e}")
            return
        self._reload_current()

    def _rebuild_destination_buttons(self) -> None:
        while self._dest_column.count():
            item = self._dest_column.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._dest_buttons.clear()

        for i, dest in enumerate(self._config.destinations):
            key = str(i + 1) if i < 9 else " "
            btn = QPushButton(f"[{key}]  {dest.name}")
            btn.setMinimumHeight(48)
            btn.clicked.connect(lambda _checked=False, idx=i: self.move_to_destination(idx))
            self._dest_column.addWidget(btn)
            self._dest_buttons.append(btn)
        self._dest_column.addStretch(1)

    def _reload_current(self) -> None:
        current = self._fm.current()
        if current is None:
            self._media.clear()
            if not self._config.source_folder:
                self._status.setText("Choose a source folder in Settings")
            elif self._fm.count == 0:
                self._status.setText("No more files in this folder")
            else:
                self._status.setText("")
            self._set_buttons_enabled(has_current=False)
            return
        self._media.load(current)
        self._status.setText(f"{current.name}    ({self._fm.index + 1} / {self._fm.count})")
        self._set_buttons_enabled(has_current=True)

    def _set_buttons_enabled(self, *, has_current: bool) -> None:
        self._prev_btn.setEnabled(has_current)
        self._next_btn.setEnabled(has_current)
        for btn in self._dest_buttons:
            btn.setEnabled(has_current)
        self._undo_btn.setEnabled(bool(self._undo_stack))
