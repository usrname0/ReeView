from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from .file_manager import IMAGE_EXTS, VIDEO_EXTS


class MediaWidget(QWidget):
    loop_toggled = Signal(bool)
    mute_toggled = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._current_path: Path | None = None
        self._loop_enabled: bool = False

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setMinimumSize(1, 1)
        self._image_label.setStyleSheet("background-color: #111; color: #888;")
        self._image_label.setText("No file loaded")

        video_page = QWidget()
        v_layout = QVBoxLayout(video_page)
        v_layout.setContentsMargins(0, 0, 0, 0)

        self._video_widget = QVideoWidget()
        self._player = QMediaPlayer()
        self._audio = QAudioOutput()
        self._player.setVideoOutput(self._video_widget)
        self._player.setAudioOutput(self._audio)

        self._play_btn = QPushButton("Pause")
        self._play_btn.clicked.connect(self.toggle_play)
        self._seek = QSlider(Qt.Horizontal)
        self._seek.sliderMoved.connect(self._player.setPosition)
        self._mute_btn = QPushButton("Mute")
        self._mute_btn.setCheckable(True)
        self._mute_btn.toggled.connect(self._on_mute_toggled)
        self._loop_btn = QPushButton("Loop")
        self._loop_btn.setCheckable(True)
        self._loop_btn.toggled.connect(self._on_loop_toggled)

        controls = QHBoxLayout()
        controls.addWidget(self._play_btn)
        controls.addWidget(self._seek, 1)
        controls.addWidget(self._loop_btn)
        controls.addWidget(self._mute_btn)

        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._seek.setMaximum)
        self._player.playbackStateChanged.connect(self._on_state)

        v_layout.addWidget(self._video_widget, 1)
        v_layout.addLayout(controls)

        self._stack = QStackedLayout()
        self._stack.addWidget(self._image_label)
        self._stack.addWidget(video_page)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(self._stack)

    def clear(self) -> None:
        self.release_current()
        self._pixmap = None
        self._current_path = None
        self._image_label.setPixmap(QPixmap())
        self._image_label.setText("No file loaded")
        self._stack.setCurrentIndex(0)

    def release_current(self) -> None:
        """Stop playback and drop the open file handle.

        Windows holds an exclusive read lock on the playing video, so we must
        clear the source before any operation that needs to move/delete it.
        """
        self._player.stop()
        self._player.setSource(QUrl())

    def load(self, path: Path) -> None:
        self._current_path = path
        ext = path.suffix.lower()
        if ext in VIDEO_EXTS:
            self._pixmap = None
            self._apply_loop_to_player()
            self._player.setSource(QUrl.fromLocalFile(str(path)))
            self._player.play()
            self._stack.setCurrentIndex(1)
        elif ext in IMAGE_EXTS:
            self._player.stop()
            self._player.setSource(QUrl())
            self._pixmap = QPixmap(str(path))
            self._update_image()
            self._stack.setCurrentIndex(0)
        else:
            self.clear()

    def _update_image(self) -> None:
        if self._pixmap is None or self._pixmap.isNull():
            name = self._current_path.name if self._current_path else ""
            self._image_label.setPixmap(QPixmap())
            self._image_label.setText(f"Could not load {name}")
            return
        scaled = self._pixmap.scaled(
            self._image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._image_label.setPixmap(scaled)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt signature)
        super().resizeEvent(event)
        if self._pixmap is not None:
            self._update_image()

    def toggle_play(self) -> None:
        if self._stack.currentIndex() != 1:
            return
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def is_video_active(self) -> bool:
        return self._stack.currentIndex() == 1

    def skip(self, seconds: float) -> None:
        if not self.is_video_active():
            return
        new_pos = self._player.position() + int(seconds * 1000)
        new_pos = max(0, new_pos)
        duration = self._player.duration()
        if duration > 0:
            new_pos = min(new_pos, duration)
        self._player.setPosition(new_pos)

    def set_loop_enabled(self, enabled: bool) -> None:
        if self._loop_enabled == enabled and self._loop_btn.isChecked() == enabled:
            return
        self._loop_enabled = enabled
        # Block signals so we don't re-emit loop_toggled when syncing the button.
        self._loop_btn.blockSignals(True)
        self._loop_btn.setChecked(enabled)
        self._loop_btn.blockSignals(False)
        self._apply_loop_to_player()

    def _on_loop_toggled(self, checked: bool) -> None:
        self._loop_enabled = checked
        self._apply_loop_to_player()
        self.loop_toggled.emit(checked)

    def set_muted(self, muted: bool) -> None:
        if self._audio.isMuted() == muted and self._mute_btn.isChecked() == muted:
            return
        self._audio.setMuted(muted)
        self._mute_btn.blockSignals(True)
        self._mute_btn.setChecked(muted)
        self._mute_btn.blockSignals(False)

    def _on_mute_toggled(self, checked: bool) -> None:
        self._audio.setMuted(checked)
        self.mute_toggled.emit(checked)

    def _apply_loop_to_player(self) -> None:
        loops = QMediaPlayer.Infinite if self._loop_enabled else 1
        self._player.setLoops(loops)

    def _on_position(self, pos: int) -> None:
        if not self._seek.isSliderDown():
            self._seek.setValue(pos)

    def _on_state(self, state) -> None:
        self._play_btn.setText("Pause" if state == QMediaPlayer.PlayingState else "Play")
