from __future__ import annotations

import bisect
import shutil
from dataclasses import dataclass
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
SUPPORTED_EXTS = IMAGE_EXTS | VIDEO_EXTS


@dataclass(frozen=True)
class Move:
    src: Path
    dst: Path


class FileManager:
    def __init__(self) -> None:
        self._files: list[Path] = []
        self._index: int = 0

    def set_source(self, path: Path | None) -> None:
        if path is None or not path.is_dir():
            self._files = []
            self._index = 0
            return
        files = [
            p for p in path.iterdir()
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
        ]
        files.sort(key=lambda p: p.name.lower())
        self._files = files
        self._index = 0

    @property
    def index(self) -> int:
        return self._index

    @property
    def count(self) -> int:
        return len(self._files)

    def current(self) -> Path | None:
        if not self._files:
            return None
        return self._files[self._index]

    def next(self) -> Path | None:
        if not self._files:
            return None
        if self._index < len(self._files) - 1:
            self._index += 1
        return self.current()

    def prev(self) -> Path | None:
        if not self._files:
            return None
        if self._index > 0:
            self._index -= 1
        return self.current()

    @staticmethod
    def _resolve_collision(target: Path) -> Path:
        if not target.exists():
            return target
        stem, suffix, parent = target.stem, target.suffix, target.parent
        i = 1
        while True:
            candidate = parent / f"{stem}_{i}{suffix}"
            if not candidate.exists():
                return candidate
            i += 1

    def move_current_to(self, dest_dir: Path) -> Move | None:
        if not self._files:
            return None
        src = self._files[self._index]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dst = self._resolve_collision(dest_dir / src.name)
        shutil.move(str(src), str(dst))
        del self._files[self._index]
        if self._index >= len(self._files) and self._index > 0:
            self._index -= 1
        return Move(src=src, dst=dst)

    def undo(self, move: Move) -> Path:
        target = self._resolve_collision(move.src)
        shutil.move(str(move.dst), str(target))
        names = [p.name.lower() for p in self._files]
        pos = bisect.bisect_left(names, target.name.lower())
        self._files.insert(pos, target)
        self._index = pos
        return target
