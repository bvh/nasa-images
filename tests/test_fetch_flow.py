import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from nasa_images.fetch import fetch_album_by_name, fetch_media_by_id


def _fake_asset(okay: bool = True, items=None) -> MagicMock:
    mock = MagicMock()
    mock.okay = okay
    mock.data = {"collection": {"items": items or []}} if okay else None
    return mock


def _fake_album_page(items, has_next: bool = False) -> MagicMock:
    m = MagicMock()
    m.okay = True
    m.data = {
        "collection": {
            "items": items,
            "links": [{"rel": "next"}] if has_next else [],
        }
    }
    return m


class TestFetchMediaById(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.catalog = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_skips_already_in_catalog(self):
        idx = {"id-1"}
        with patch("nasa_images.fetch.Asset") as Asset:
            result = fetch_media_by_id("id-1", self.catalog, idx)
        Asset.assert_not_called()
        self.assertTrue(result)

    def test_asset_not_okay_returns_false(self):
        with patch("nasa_images.fetch.Asset", return_value=_fake_asset(okay=False)):
            result = fetch_media_by_id("id-1", self.catalog, set())
        self.assertFalse(result)

    def test_missing_orig_returns_false(self):
        asset = _fake_asset(items=[{"href": "https://x/metadata.json"}])
        with patch("nasa_images.fetch.Asset", return_value=asset):
            result = fetch_media_by_id("id-1", self.catalog, set())
        self.assertFalse(result)

    def test_happy_path(self):
        items = [
            {"href": "https://x/foo~orig.jpg"},
            {"href": "https://x/metadata.json"},
        ]
        asset = _fake_asset(items=items)
        meta = {"AVAIL:DateCreated": "2024-01-02"}
        with (
            patch("nasa_images.fetch.Asset", return_value=asset),
            patch("nasa_images.fetch._load_metadata_json", return_value=meta),
            patch("nasa_images.fetch._download_file") as dl,
        ):
            idx: set[str] = set()
            result = fetch_media_by_id("id-1", self.catalog, idx)

        self.assertTrue(result)
        self.assertIn("id-1", idx)
        dl.assert_called_once()
        dest_dir = self.catalog / "2024" / "01" / "2024-01-02" / "id-1"
        self.assertTrue(dest_dir.exists())
        self.assertTrue((dest_dir / "metadata.json").exists())

    def test_happy_path_unknown_date(self):
        items = [{"href": "https://x/foo~orig.jpg"}]
        asset = _fake_asset(items=items)
        with (
            patch("nasa_images.fetch.Asset", return_value=asset),
            patch("nasa_images.fetch._load_metadata_json", return_value=None),
            patch("nasa_images.fetch._download_file"),
        ):
            fetch_media_by_id("id-1", self.catalog, set())
        self.assertTrue((self.catalog / "unknown" / "id-1").exists())

    def test_existing_files_not_overwritten(self):
        items = [
            {"href": "https://x/foo~orig.jpg"},
            {"href": "https://x/metadata.json"},
        ]
        asset = _fake_asset(items=items)
        meta = {"AVAIL:DateCreated": "2024-01-02"}
        dest_dir = self.catalog / "2024" / "01" / "2024-01-02" / "id-1"
        dest_dir.mkdir(parents=True)
        (dest_dir / "foo~orig.jpg").write_bytes(b"existing")
        (dest_dir / "metadata.json").write_text('{"keep": true}')

        with (
            patch("nasa_images.fetch.Asset", return_value=asset),
            patch("nasa_images.fetch._load_metadata_json", return_value=meta),
            patch("nasa_images.fetch._download_file") as dl,
        ):
            fetch_media_by_id("id-1", self.catalog, set())

        dl.assert_not_called()
        self.assertEqual((dest_dir / "foo~orig.jpg").read_bytes(), b"existing")
        self.assertEqual((dest_dir / "metadata.json").read_text(), '{"keep": true}')


class TestFetchAlbumByName(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.catalog = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_pagination_walks_all_pages(self):
        page1 = _fake_album_page(
            [{"data": [{"nasa_id": "a", "media_type": "image"}]}], has_next=True
        )
        page2 = _fake_album_page(
            [{"data": [{"nasa_id": "b", "media_type": "image"}]}]
        )
        with (
            patch("nasa_images.fetch.Album", side_effect=[page1, page2]),
            patch(
                "nasa_images.fetch.fetch_media_by_id", return_value=True
            ) as fm,
            patch("nasa_images.fetch.time.sleep"),
        ):
            fetch_album_by_name("album", self.catalog)
        self.assertEqual([c.args[0] for c in fm.call_args_list], ["a", "b"])

    def test_media_type_filter(self):
        page = _fake_album_page(
            [
                {"data": [{"nasa_id": "a", "media_type": "image"}]},
                {"data": [{"nasa_id": "b", "media_type": "video"}]},
                {"data": [{"nasa_id": "c", "media_type": "image"}]},
            ]
        )
        with (
            patch("nasa_images.fetch.Album", return_value=page),
            patch(
                "nasa_images.fetch.fetch_media_by_id", return_value=True
            ) as fm,
            patch("nasa_images.fetch.time.sleep"),
        ):
            fetch_album_by_name("album", self.catalog, media_type="image")
        self.assertEqual([c.args[0] for c in fm.call_args_list], ["a", "c"])

    def test_continues_on_per_item_exception(self):
        page = _fake_album_page(
            [
                {"data": [{"nasa_id": "a", "media_type": "image"}]},
                {"data": [{"nasa_id": "b", "media_type": "image"}]},
                {"data": [{"nasa_id": "c", "media_type": "image"}]},
            ]
        )

        def side_effect(nasa_id, *args, **kwargs):
            if nasa_id == "b":
                raise RuntimeError("download failed")
            return True

        with (
            patch("nasa_images.fetch.Album", return_value=page),
            patch(
                "nasa_images.fetch.fetch_media_by_id", side_effect=side_effect
            ) as fm,
            patch("nasa_images.fetch.time.sleep"),
        ):
            fetch_album_by_name("album", self.catalog)
        self.assertEqual(fm.call_count, 3)

    def test_missing_nasa_id_is_skipped(self):
        page = _fake_album_page(
            [
                {"data": [{"media_type": "image"}]},
                {"data": [{"nasa_id": "a", "media_type": "image"}]},
            ]
        )
        with (
            patch("nasa_images.fetch.Album", return_value=page),
            patch(
                "nasa_images.fetch.fetch_media_by_id", return_value=True
            ) as fm,
            patch("nasa_images.fetch.time.sleep"),
        ):
            fetch_album_by_name("album", self.catalog)
        self.assertEqual([c.args[0] for c in fm.call_args_list], ["a"])

    def test_album_not_okay_breaks_cleanly(self):
        bad = MagicMock()
        bad.okay = False
        bad.data = None
        with (
            patch("nasa_images.fetch.Album", return_value=bad),
            patch("nasa_images.fetch.fetch_media_by_id") as fm,
            patch("nasa_images.fetch.time.sleep"),
        ):
            fetch_album_by_name("album", self.catalog)
        fm.assert_not_called()
