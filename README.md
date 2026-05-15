# ReeView

A fast, keyboard-driven sorter for folders full of images and videos. Point it
at a folder, configure a handful of destination folders, and use single-key
hotkeys to flick each file to wherever it belongs.

Built on PySide6 (Qt 6) for snappy clicks, real keyboard shortcuts, and
first-class video playback.

<!-- screenshots: drop image links here later -->

## Features

- **One-key sorting.** Press `1`–`9` (or click) to move the current file to
  the matching destination folder.
- **Image + video viewer.** Images render scaled-to-fit and re-scale on window
  resize. Videos play inline with play/pause, scrub bar, mute, and loop
  controls (QtMultimedia backend — uses Windows Media Foundation on Windows).
- **Full in-session undo.** `Ctrl+Z` (or the Undo button) reverses any number
  of moves in reverse order, restoring each file to its original location.
- **Collision-safe moves.** When the destination already has a file with the
  same name, ReeView appends `_1`, `_2`, … to the moved file's stem until the
  name is unique — never overwrites, never blocks the workflow.
- **Configurable video skip.** `Shift+←` / `Shift+→` seek within the current
  video by a configurable number of seconds (default 5, range 1–600).
- **Persistent settings.** Source folder, destinations, window geometry, loop
  toggle, mute toggle, and skip step all survive across restarts.

## Installation

ReeView targets Python 3.10+ (developed against 3.13) on Windows, macOS, and
Linux. PySide6 is the only runtime dependency.

```bash
# from the repo root
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

## Running

Once the venv is set up, use the launcher for your platform:

- **Windows:** double-click `run.bat` or run it from a shell.
- **macOS / Linux:** `./run.sh` (run `chmod +x run.sh` once if needed).

Either launcher just activates the venv and runs `python -m reeview`, so you
can do that directly too.

## Usage

### 1. Configure (Settings tab)

- **Source folder** — the folder full of files you want to sort through.
  ReeView lists supported media at the top level only (it does not recurse
  into subfolders).
- **Destinations** — add as many as you like with `Add...`. Each destination
  has a display name and a folder path. The first nine are reachable via
  hotkeys `1`–`9` in list order; reorder them with `Move Up` / `Move Down`.
- **Video skip step** — number of seconds `Shift+←` / `Shift+→` jumps within
  a video.

### 2. Sort (View tab)

The current file fills the main pane. The right column shows one button per
destination, labelled with its hotkey. The bottom row has Prev / Next / Undo
and a status label showing the filename and position (e.g. `12 / 200`).

### Keyboard shortcuts

| Key                    | Action                                       |
| ---------------------- | -------------------------------------------- |
| `→`                    | Next file                                    |
| `←`                    | Previous file                                |
| `1` – `9`              | Move current file to destination 1–9         |
| `Space`                | Play / pause the current video               |
| `Shift+→` / `Shift+←`  | Seek video forward / back by the skip step   |
| `Ctrl+Z`               | Undo last move                               |

Shortcuts only fire while the View tab has focus, so typing in Settings
fields won't trigger sorts.

### Supported file types

- **Images:** `.jpg .jpeg .png .gif .webp .bmp .tiff .tif`
- **Videos:** `.mp4 .mov .avi .mkv .webm .m4v`

Files with other extensions are ignored.

## Config file

Settings live at `~/.reeview/config.json` (e.g.
`C:\Users\<you>\.reeview\config.json` on Windows). It's plain JSON — safe to
inspect, edit by hand, or back up. Fields:

| Field                 | Type            | Notes                                     |
| --------------------- | --------------- | ----------------------------------------- |
| `source_folder`       | string \| null  | Last picked source folder                 |
| `destinations`        | array of `{name, path}` | In hotkey order                   |
| `window_geometry`     | base64 string   | Restored on launch                        |
| `loop_video`          | bool            | Mirrors the Loop button in video controls |
| `muted`               | bool            | Mirrors the Mute button                   |
| `video_skip_seconds`  | int             | 1–600                                     |

## Development

Pure-Python unit tests cover the file manager (source listing, move,
collision handling, undo, index clamping):

```bash
venv\Scripts\python -m unittest tests.test_file_manager -v
```

## License

See [LICENSE](LICENSE).
