import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reeview.file_manager import FileManager  # noqa: E402


class FileManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="reeview-"))
        self.src = self.tmp / "src"
        self.dst = self.tmp / "dst"
        self.src.mkdir()
        self.dst.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _touch(self, parent: Path, name: str, content: bytes = b"x") -> Path:
        p = parent / name
        p.write_bytes(content)
        return p

    def test_collision_appends_suffix(self):
        self._touch(self.src, "a.jpg", b"src")
        self._touch(self.dst, "a.jpg", b"existing")
        fm = FileManager()
        fm.set_source(self.src)
        move = fm.move_current_to(self.dst)
        self.assertIsNotNone(move)
        self.assertEqual(move.dst.name, "a_1.jpg")
        self.assertEqual(move.dst.read_bytes(), b"src")
        self.assertEqual((self.dst / "a.jpg").read_bytes(), b"existing")
        self.assertFalse((self.src / "a.jpg").exists())

    def test_collision_increments_until_unique(self):
        self._touch(self.src, "a.jpg")
        self._touch(self.dst, "a.jpg")
        self._touch(self.dst, "a_1.jpg")
        self._touch(self.dst, "a_2.jpg")
        fm = FileManager()
        fm.set_source(self.src)
        move = fm.move_current_to(self.dst)
        self.assertEqual(move.dst.name, "a_3.jpg")

    def test_move_then_undo_roundtrip(self):
        self._touch(self.src, "a.jpg")
        self._touch(self.src, "b.png")
        fm = FileManager()
        fm.set_source(self.src)
        self.assertEqual(fm.current().name, "a.jpg")
        move = fm.move_current_to(self.dst)
        self.assertEqual(fm.count, 1)
        self.assertEqual(fm.current().name, "b.png")
        fm.undo(move)
        self.assertEqual(fm.count, 2)
        self.assertEqual(fm.current().name, "a.jpg")
        self.assertTrue((self.src / "a.jpg").exists())
        self.assertFalse((self.dst / "a.jpg").exists())

    def test_index_clamps_after_moving_last_file(self):
        self._touch(self.src, "a.jpg")
        self._touch(self.src, "b.png")
        fm = FileManager()
        fm.set_source(self.src)
        fm.next()
        self.assertEqual(fm.index, 1)
        fm.move_current_to(self.dst)
        self.assertEqual(fm.index, 0)
        self.assertEqual(fm.current().name, "a.jpg")

    def test_empty_source_returns_none(self):
        fm = FileManager()
        fm.set_source(self.src)
        self.assertIsNone(fm.current())
        self.assertIsNone(fm.move_current_to(self.dst))

    def test_unsupported_extensions_ignored(self):
        self._touch(self.src, "doc.txt")
        self._touch(self.src, "pic.jpg")
        fm = FileManager()
        fm.set_source(self.src)
        self.assertEqual(fm.count, 1)
        self.assertEqual(fm.current().name, "pic.jpg")

    def test_undo_reinserts_in_sorted_position(self):
        self._touch(self.src, "a.jpg")
        self._touch(self.src, "c.jpg")
        fm = FileManager()
        fm.set_source(self.src)
        move = fm.move_current_to(self.dst)
        # Simulate a new file appearing in source between a and c
        self._touch(self.src, "b.jpg")
        fm.set_source(self.src)
        fm.undo(move)
        names = [fm._files[i].name for i in range(fm.count)]
        self.assertEqual(names, ["a.jpg", "b.jpg", "c.jpg"])
        self.assertEqual(fm.current().name, "a.jpg")


if __name__ == "__main__":
    unittest.main()
