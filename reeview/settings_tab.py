from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .config import Config, Destination


class SettingsTab(QWidget):
    config_changed = Signal()

    def __init__(self, config: Config, parent=None) -> None:
        super().__init__(parent)
        self._config = config

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Source folder:"))
        self._src_edit = QLineEdit(config.source_folder or "")
        self._src_edit.setReadOnly(True)
        src_browse = QPushButton("Browse...")
        src_browse.clicked.connect(self._pick_source)
        src_row = QHBoxLayout()
        src_row.addWidget(self._src_edit, 1)
        src_row.addWidget(src_browse)
        layout.addLayout(src_row)

        layout.addSpacing(12)
        layout.addWidget(QLabel("Destinations (hotkeys 1–9 in list order):"))
        self._dest_list = QListWidget()
        layout.addWidget(self._dest_list, 1)

        btn_row = QHBoxLayout()
        for label, slot in (
            ("Add...", self._add_dest),
            ("Remove", self._remove_dest),
            ("Move Up", lambda: self._move_dest(-1)),
            ("Move Down", lambda: self._move_dest(1)),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        layout.addSpacing(12)
        skip_row = QHBoxLayout()
        skip_row.addWidget(QLabel("Video skip step (Shift+←/→):"))
        self._skip_spin = QSpinBox()
        self._skip_spin.setRange(1, 600)
        self._skip_spin.setSuffix(" s")
        self._skip_spin.setValue(config.video_skip_seconds)
        self._skip_spin.valueChanged.connect(self._on_skip_changed)
        skip_row.addWidget(self._skip_spin)
        skip_row.addStretch(1)
        layout.addLayout(skip_row)

        self._refresh_dest_list()

    def _refresh_dest_list(self) -> None:
        self._dest_list.clear()
        for i, d in enumerate(self._config.destinations):
            key = str(i + 1) if i < 9 else "·"
            self._dest_list.addItem(f"[{key}]  {d.name}  —  {d.path}")

    def _pick_source(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Choose source folder", self._src_edit.text() or ""
        )
        if not path:
            return
        self._src_edit.setText(path)
        self._config.source_folder = path
        self._save_and_emit()

    def _add_dest(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose destination folder")
        if not path:
            return
        default_name = Path(path).name or path
        name, ok = QInputDialog.getText(
            self, "Destination name", "Display name:", text=default_name
        )
        if not ok or not name.strip():
            return
        self._config.destinations.append(Destination(name=name.strip(), path=path))
        self._refresh_dest_list()
        self._save_and_emit()

    def _remove_dest(self) -> None:
        row = self._dest_list.currentRow()
        if row < 0:
            return
        del self._config.destinations[row]
        self._refresh_dest_list()
        self._save_and_emit()

    def _move_dest(self, delta: int) -> None:
        row = self._dest_list.currentRow()
        new_row = row + delta
        if row < 0 or new_row < 0 or new_row >= len(self._config.destinations):
            return
        ds = self._config.destinations
        ds[row], ds[new_row] = ds[new_row], ds[row]
        self._refresh_dest_list()
        self._dest_list.setCurrentRow(new_row)
        self._save_and_emit()

    def _on_skip_changed(self, value: int) -> None:
        self._config.video_skip_seconds = value
        self._save_and_emit()

    def _save_and_emit(self) -> None:
        self._config.save()
        self.config_changed.emit()
