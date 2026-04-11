import unittest
from datetime import date
from pathlib import Path

from nasa_images.fetch import _ORIG_RE, _asset_urls, _destination, _extract_date


class TestOrigRe(unittest.TestCase):
    def test_matches_orig_jpg(self):
        self.assertIsNotNone(_ORIG_RE.search("foo~orig.jpg"))

    def test_matches_orig_tif(self):
        self.assertIsNotNone(_ORIG_RE.search("image~orig.tif"))

    def test_rejects_thumb(self):
        self.assertIsNone(_ORIG_RE.search("foo~thumb.jpg"))

    def test_rejects_extension_with_dot(self):
        self.assertIsNone(_ORIG_RE.search("foo~orig.tar.gz"))

    def test_rejects_extension_with_slash(self):
        self.assertIsNone(_ORIG_RE.search("foo~orig.jp/g"))


class TestExtractDate(unittest.TestCase):
    def test_exif_datetime_original(self):
        self.assertEqual(
            _extract_date({"EXIF:DateTimeOriginal": "2024:06:15 12:34:56"}),
            date(2024, 6, 15),
        )

    def test_exif_create_date_fallback(self):
        self.assertEqual(
            _extract_date({"EXIF:CreateDate": "2023:01:02 00:00:00"}),
            date(2023, 1, 2),
        )

    def test_avail_iso8601(self):
        self.assertEqual(
            _extract_date({"AVAIL:DateCreated": "2022-03-04T05:06:07Z"}),
            date(2022, 3, 4),
        )

    def test_avail_short_date(self):
        self.assertEqual(
            _extract_date({"AVAIL:DateCreated": "2021-07-08"}),
            date(2021, 7, 8),
        )

    def test_avail_colon_date(self):
        self.assertEqual(
            _extract_date({"AVAIL:DateCreated": "2020:11:12"}),
            date(2020, 11, 12),
        )

    def test_prefers_exif_over_avail(self):
        meta = {
            "EXIF:DateTimeOriginal": "2024:06:15 12:34:56",
            "AVAIL:DateCreated": "2020-01-01",
        }
        self.assertEqual(_extract_date(meta), date(2024, 6, 15))

    def test_empty_meta(self):
        self.assertIsNone(_extract_date({}))

    def test_malformed_value(self):
        self.assertIsNone(_extract_date({"AVAIL:DateCreated": "not-a-date"}))

    def test_non_string_value(self):
        self.assertIsNone(_extract_date({"EXIF:DateTimeOriginal": 12345}))

    def test_empty_string_value(self):
        self.assertIsNone(_extract_date({"EXIF:DateTimeOriginal": ""}))


class TestDestination(unittest.TestCase):
    def test_dated_path(self):
        result = _destination(Path("/cat"), "abc", date(2024, 5, 6))
        self.assertEqual(result, Path("/cat/2024/05/2024-05-06/abc"))

    def test_unknown_path(self):
        result = _destination(Path("/cat"), "abc", None)
        self.assertEqual(result, Path("/cat/unknown/abc"))

    def test_zero_padding(self):
        result = _destination(Path("/cat"), "abc", date(7, 1, 2))
        self.assertEqual(result, Path("/cat/0007/01/0007-01-02/abc"))


class TestAssetUrls(unittest.TestCase):
    def test_picks_orig_and_metadata(self):
        data = {
            "collection": {
                "items": [
                    {"href": "https://x/y/img~thumb.jpg"},
                    {"href": "https://x/y/img~orig.jpg"},
                    {"href": "https://x/y/metadata.json"},
                ]
            }
        }
        orig, meta = _asset_urls(data)
        self.assertEqual(orig, "https://x/y/img~orig.jpg")
        self.assertEqual(meta, "https://x/y/metadata.json")

    def test_missing_orig(self):
        data = {"collection": {"items": [{"href": "https://x/y/metadata.json"}]}}
        orig, meta = _asset_urls(data)
        self.assertIsNone(orig)
        self.assertEqual(meta, "https://x/y/metadata.json")

    def test_missing_metadata(self):
        data = {"collection": {"items": [{"href": "https://x/y/img~orig.jpg"}]}}
        orig, meta = _asset_urls(data)
        self.assertEqual(orig, "https://x/y/img~orig.jpg")
        self.assertIsNone(meta)

    def test_empty_collection(self):
        self.assertEqual(_asset_urls({}), (None, None))
        self.assertEqual(_asset_urls({"collection": {}}), (None, None))

    def test_ignores_falsy_hrefs(self):
        data = {"collection": {"items": [{"href": None}, {"href": ""}]}}
        self.assertEqual(_asset_urls(data), (None, None))
