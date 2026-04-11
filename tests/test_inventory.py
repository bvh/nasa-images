import tempfile
import unittest
from pathlib import Path

from inventory import inventory


class TestInventory(unittest.TestCase):
    def test_dated_leaf_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for nasa_id in ("abc", "def"):
                d = root / "2024" / "05" / "2024-05-06" / nasa_id
                d.mkdir(parents=True)
                (d / "img.jpg").write_bytes(b"x")
            self.assertEqual(inventory(root), ["abc", "def"])

    def test_unknown_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "unknown" / "xyz"
            d.mkdir(parents=True)
            (d / "img.jpg").write_bytes(b"x")
            self.assertEqual(inventory(root), ["xyz"])

    def test_mixed_dated_and_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d1 = root / "2024" / "05" / "2024-05-06" / "abc"
            d2 = root / "unknown" / "xyz"
            for d in (d1, d2):
                d.mkdir(parents=True)
                (d / "img.jpg").write_bytes(b"x")
            self.assertEqual(inventory(root), ["abc", "xyz"])

    @unittest.expectedFailure
    def test_empty_dirs_should_not_appear(self):
        # Review item #5: empty dirs currently leak into results because
        # `any(p.is_dir() for p in iterdir())` returns False on an empty
        # directory, so it's classified as a leaf. Tracked as expectedFailure
        # until the bug is fixed.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "unknown" / "empty").mkdir(parents=True)
            self.assertEqual(inventory(root), [])
