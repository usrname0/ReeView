from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONFIG_PATH = Path.home() / ".reeview" / "config.json"


@dataclass
class Destination:
    name: str
    path: str


@dataclass
class Config:
    source_folder: str | None = None
    destinations: list[Destination] = field(default_factory=list)
    window_geometry: str | None = None
    loop_video: bool = False
    video_skip_seconds: int = 5
    muted: bool = False

    @classmethod
    def load(cls) -> "Config":
        if not CONFIG_PATH.exists():
            return cls()
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        dests = [Destination(**d) for d in data.get("destinations", [])]
        return cls(
            source_folder=data.get("source_folder"),
            destinations=dests,
            window_geometry=data.get("window_geometry"),
            loop_video=bool(data.get("loop_video", False)),
            video_skip_seconds=int(data.get("video_skip_seconds", 5)),
            muted=bool(data.get("muted", False)),
        )

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "source_folder": self.source_folder,
            "destinations": [asdict(d) for d in self.destinations],
            "window_geometry": self.window_geometry,
            "loop_video": self.loop_video,
            "video_skip_seconds": self.video_skip_seconds,
            "muted": self.muted,
        }
        CONFIG_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
