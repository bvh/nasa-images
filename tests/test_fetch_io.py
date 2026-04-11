import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nasa_images.fetch import (
    _catalog_index_path,
    _download_file,
    _load_catalog_index,
    _save_catalog_index,
    _write_metadata,
)


class _FakeUrlopenCM:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self):
        return io.BytesIO(self._payload)

    def __exit__(self, *a):
        return False


class TestCatalogIndex(unittest.TestCase):
    def test_load_missing_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(_load_catalog_index(Path(tmp)), set())

    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            cat = Path(tmp)
            _save_catalog_index(cat, {"b", "a", "c"})
            self.assertEqual(_load_catalog_index(cat), {"a", "b", "c"})

    def test_save_writes_sorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            cat = Path(tmp)
            _save_catalog_index(cat, {"zeta", "alpha", "mu"})
            text = _catalog_index_path(cat).read_text()
            self.assertEqual(text.splitlines(), ["alpha", "mu", "zeta"])


class TestWriteMetadata(unittest.TestCase):
    def test_writes_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metadata.json"
            _write_metadata({"k": "v", "n": 1}, path)
            self.assertEqual(json.loads(path.read_text()), {"k": "v", "n": 1})


class TestDownloadFile(unittest.TestCase):
    def test_success_renames_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "img.jpg"
            with patch(
                "nasa_images.fetch.urllib.request.urlopen",
                return_value=_FakeUrlopenCM(b"payload"),
            ):
                _download_file("https://x/y/img.jpg", dest)
            self.assertEqual(dest.read_bytes(), b"payload")
            self.assertFalse(dest.with_suffix(".jpg.part").exists())

    def test_failure_cleans_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "img.jpg"
            with patch(
                "nasa_images.fetch.urllib.request.urlopen",
                side_effect=RuntimeError("boom"),
            ):
                with self.assertRaises(RuntimeError):
                    _download_file("https://x/y/img.jpg", dest)
            self.assertFalse(dest.exists())
            self.assertFalse(dest.with_suffix(".jpg.part").exists())

    def test_replaces_spaces_in_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "img.jpg"
            with patch(
                "nasa_images.fetch.urllib.request.urlopen",
                return_value=_FakeUrlopenCM(b"x"),
            ) as m:
                _download_file("https://x/y/my file.jpg", dest)
            m.assert_called_once_with("https://x/y/my%20file.jpg")
