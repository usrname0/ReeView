# ReeView — Developer Notes

Project-specific design notes, conventions, and gotchas. For user-facing
docs (install, usage, shortcuts) see [README.md](README.md).

## Architecture map

Everything lives under the `reeview/` package. Modules are intentionally
single-purpose and the Qt vs. pure-Python split is strict:

| Module             | Qt deps | Role                                                                    |
| ------------------ | :-----: | ----------------------------------------------------------------------- |
| `config.py`        |  none   | Dataclass + JSON load/save at `~/.reeview/config.json`. All persistence. |
| `file_manager.py`  |  none   | Source listing, current index, move + undo. Pure logic — unit-tested.  |
| `media_widget.py`  |   Qt    | Image + video display via `QStackedLayout`. Owns the `QMediaPlayer`.   |
| `view_tab.py`      |   Qt    | Orchestrates sorting: wires media, file manager, undo stack, destinations. |
| `settings_tab.py`  |   Qt    | Edits config (source, destinations, skip step). Emits `config_changed`. |
| `main_window.py`   |   Qt    | `QTabWidget` shell. Installs global shortcuts. Persists window geometry. |
| `app.py` / `__main__.py` | Qt | Entry points. `python -m reeview` calls `app.run()`.                  |

Data flow for a sort:

```
keypress / button click
  → main_window QShortcut OR view_tab destination button
  → view_tab.move_to_destination(idx)
    → media_widget.release_current()        (drops video file handle)
    → file_manager.move_current_to(dest)   (shutil.move + collision rename)
    → view_tab.undo_stack.append(move)
    → view_tab._reload_current()           (loads next file in media_widget)
```

## Conventions

### Config-backed UI toggles

For any user-toggleable state that should survive restart, follow this
pattern (used by `loop_video`, `muted`, `video_skip_seconds`):

1. Add a field with a default to `Config` in `config.py`; update `load()`
   and `save()`.
2. In `media_widget.py`, expose:
   - A `set_<name>(value)` setter that updates Qt state *and* the visible
     widget, with `blockSignals` around the widget update so syncing doesn't
     re-emit.
   - A `<name>_toggled` `Signal(...)` emitted only by genuine user input
     (e.g. `_on_loop_toggled`), not by `set_<name>`.
3. In `view_tab.py`'s `__init__`, call `self._media.set_<name>(config.<name>)`
   and connect `<name>_toggled` to a private slot that writes back to config
   and calls `self._config.save()`.

The split between "setter syncs without echo" and "user-triggered signal
emits" is what prevents infinite loops when initialising from config.

### Pure-Python core, Qt at the edges

`file_manager.py` and `config.py` deliberately have zero Qt imports. This is
what lets `tests/test_file_manager.py` run fast under plain `python -m
unittest`. Don't reach for `QFileSystemWatcher` / `QSettings` / etc. unless
there's a real need — JSON + `pathlib` does the job.

### Shortcuts only fire on the View tab

Global `QShortcut`s in `main_window._install_shortcuts` are gated by
`self._on_view_tab()`. This keeps `1`–`9` from triggering sorts while the
user is editing fields on the Settings tab. The pattern is:

```python
add(Qt.Key_X, lambda: self._on_view_tab() and self._view_tab.some_action())
```

The lambda's truthy short-circuit is intentional — its return value is
ignored by Qt.

## Gotchas

### Windows holds a read lock on playing video files

`QMediaPlayer` on Windows (Media Foundation backend) keeps an exclusive
handle on the currently-loaded video. `shutil.move` against it fails with
`PermissionError` / WinError 32 ("file is being used by another process").

The fix is in `view_tab.move_to_destination`:

1. If `MediaWidget.is_video_active()`, call `MediaWidget.release_current()`
   first — that runs `player.stop()` + `player.setSource(QUrl())`.
2. Call `_move_with_retry`, which retries up to 20× with
   `QCoreApplication.processEvents()` between attempts. Source release is
   asynchronous on WinMF; the event pump gives the backend time to actually
   close the handle.
3. On final failure, the status bar shows the error *and* the released
   video is reloaded so the user doesn't lose context.

If you add any other path that needs to move/delete the currently-shown
file, route it through the same release-then-retry sequence.

### Loops via `QMediaPlayer.setLoops`

`MediaWidget._apply_loop_to_player` sets either `QMediaPlayer.Infinite`
(`-1`) or `1`. Don't reimplement looping by listening to
`mediaStatusChanged == EndOfMedia` — `setLoops` is built in since Qt 6.4 and
handles the seek-back internally. `_apply_loop_to_player` is called both on
toggle and at the start of each `load()` so the setting sticks across files.

### Collision-safe renames are used on both sides of undo

`FileManager._resolve_collision` is used for the move *and* for the undo:
when restoring a file to its original source folder, we still check for a
name collision in case the user added a different file with the same name
to the source in the meantime. Don't shortcut this — losing a user file on
undo would be much worse than a small suffix on restore.

### `move_current_to` updates the index in place

After moving the current file out of the list, the next file slides into
the current index. If we were at the last position, the index decrements.
The caller should always call `_reload_current()` afterward — the index
points at a *different* file (or is `None` if the list is empty).

### `MediaWidget.skip()` clamps the lower bound, not the upper

Backward seeks clamp to 0. Forward seeks only clamp to `duration` if
duration is known (`> 0`); otherwise we trust the player to handle it. This
matters when the user mashes `Shift+→` right as a video loads and Qt hasn't
reported duration yet.

## Adding things

### Adding a persistent setting

1. Add the field to `Config` (default + load + save).
2. Add a widget for it on the Settings tab; connect its change signal to a
   slot that updates `self._config` and calls `self._save_and_emit()`.
3. If it affects the View tab, either read it on demand from
   `self._config` (cheap fields like `video_skip_seconds`) or apply it via
   the `set_<name>` / `<name>_toggled` pattern above.

### Adding a keyboard shortcut

Add a single line in `main_window._install_shortcuts` using the `add(...)`
helper. Keep all shortcuts in one place so the shortcut surface stays
greppable and the View-tab gate is consistent.

### Adding a new media type

1. Extend `IMAGE_EXTS` or `VIDEO_EXTS` in `file_manager.py`.
2. If it's a new *category* (e.g. audio), add a new stack page to
   `MediaWidget` and branch on extension in `load()`.

## Testing

- **Pure-Python:** `venv\Scripts\python -m unittest tests.test_file_manager -v`
  — covers move/undo, collision suffixing, index clamping, sorted reinsert.
- **Qt smoke test:** the recurring pattern in this repo is
  `QT_QPA_PLATFORM=offscreen python -c "..."` to instantiate `MainWindow`
  and poke the relevant widget's API. Useful when changing wiring; not a
  substitute for actually launching the app and trying a real sort.
- **Don't use a real media file in unit tests.** The whole point of
  `file_manager` having no Qt deps is to keep tests fast and deterministic.

## Out of scope (deliberate)

These were considered and explicitly deferred:

- **Subfolder recursion** in the source listing. Top-level only keeps "next
  file" unambiguous.
- **Metadata read/edit.** Mentioned in the original sketch as a possible
  later phase.
- **A built-in Trash / Delete action.** A destination folder pointed at
  e.g. the OS trash directory covers the use case.
- **Drag-and-drop destination reordering.** The Up / Down buttons in
  Settings cover it without the layout complexity.
- **Persistent cross-session undo.** The undo stack is in-session only —
  `collections.deque` in `ViewTab`, cleared on close.

Don't add these without checking that the original constraint still holds.
