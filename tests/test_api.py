import unittest
from unittest.mock import patch

from nasa_images.api import (
    NASA_ALBUM_ENDPOINT,
    NASA_ASSET_ENDPOINT,
    NASA_CAPTIONS_ENDPOINT,
    NASA_METADATA_ENDPOINT,
    NASA_SEARCH_ENDPOINT,
    Album,
    Asset,
    Captions,
    Endpoint,
    Metadata,
    Search,
)
from tests.fixtures import FakeResponse


class TestCollapseItems(unittest.TestCase):
    def test_basic(self):
        items = [{"href": "a"}, {"href": "b"}]
        self.assertEqual(Endpoint.collapse_items(items, key="href"), ["a", "b"])

    def test_missing_key_yields_none(self):
        items = [{"href": "a"}, {"other": "b"}]
        self.assertEqual(Endpoint.collapse_items(items, key="href"), ["a", None])

    def test_empty(self):
        self.assertEqual(Endpoint.collapse_items([], key="href"), [])

    def test_custom_key(self):
        items = [{"nasa_id": "a"}, {"nasa_id": "b"}]
        self.assertEqual(
            Endpoint.collapse_items(items, key="nasa_id"), ["a", "b"]
        )


class TestResponseParseJson(unittest.TestCase):
    def test_200_parses(self):
        r = FakeResponse(status=200, data={"k": 1})
        self.assertEqual(r.parse_json(), {"k": 1})

    def test_non_200_returns_empty(self):
        r = FakeResponse(status=404, data={"k": 1})
        self.assertEqual(r.parse_json(), {})


class TestEndpointHttpGet(unittest.TestCase):
    def test_empty_url_returns_none(self):
        self.assertIsNone(Endpoint.http_get(""))

    def test_none_url_returns_none(self):
        self.assertIsNone(Endpoint.http_get(None))


class TestAssetEndpoint(unittest.TestCase):
    def test_okay_200(self):
        fake = FakeResponse(status=200, data={"collection": {"items": []}})
        with patch.object(Endpoint, "http_get", return_value=fake):
            asset = Asset("abc")
        self.assertTrue(asset.okay)
        self.assertEqual(asset.api_url, f"{NASA_ASSET_ENDPOINT}abc")
        self.assertEqual(asset.data, {"collection": {"items": []}})

    def test_not_okay_when_http_get_returns_none(self):
        with patch.object(Endpoint, "http_get", return_value=None):
            asset = Asset("abc")
        self.assertFalse(asset.okay)
        self.assertIsNone(asset.data)

    def test_not_okay_when_status_non_200(self):
        fake = FakeResponse(status=404, data={})
        with patch.object(Endpoint, "http_get", return_value=fake):
            asset = Asset("abc")
        self.assertFalse(asset.okay)
        self.assertIsNone(asset.data)

    def test_url_encoding_of_id_with_space(self):
        fake = FakeResponse(status=200, data={})
        with patch.object(Endpoint, "http_get", return_value=fake):
            asset = Asset("foo bar")
        self.assertEqual(asset.api_url, f"{NASA_ASSET_ENDPOINT}foo%20bar")


class TestMetadataEndpoint(unittest.TestCase):
    def test_okay(self):
        fake = FakeResponse(
            status=200, data={"EXIF:DateTimeOriginal": "2024:01:01 00:00:00"}
        )
        with patch.object(Endpoint, "http_get", return_value=fake):
            md = Metadata("abc")
        self.assertTrue(md.okay)
        self.assertEqual(md.api_url, f"{NASA_METADATA_ENDPOINT}abc")
        self.assertIn("EXIF:DateTimeOriginal", md.data)


class TestAlbumEndpoint(unittest.TestCase):
    def test_no_page(self):
        fake = FakeResponse(status=200, data={})
        with patch.object(Endpoint, "http_get", return_value=fake):
            album = Album("Artemis_II")
        self.assertEqual(album.api_url, f"{NASA_ALBUM_ENDPOINT}Artemis_II")

    def test_with_page(self):
        fake = FakeResponse(status=200, data={})
        with patch.object(Endpoint, "http_get", return_value=fake):
            album = Album("Artemis_II", page=5)
        self.assertEqual(
            album.api_url, f"{NASA_ALBUM_ENDPOINT}Artemis_II?page=5"
        )


class TestCaptionsEndpoint(unittest.TestCase):
    def test_okay(self):
        fake = FakeResponse(status=200, data={"location": "..."})
        with patch.object(Endpoint, "http_get", return_value=fake):
            c = Captions("abc")
        self.assertTrue(c.okay)
        self.assertEqual(c.api_url, f"{NASA_CAPTIONS_ENDPOINT}abc")


class TestSearchEndpoint(unittest.TestCase):
    def test_only_non_none_params(self):
        fake = FakeResponse(status=200, data={})
        with patch.object(Endpoint, "http_get", return_value=fake):
            s = Search(q="moon", media_type="image")
        self.assertIn("q=moon", s.api_url)
        self.assertIn("media_type=image", s.api_url)
        self.assertNotIn("center=", s.api_url)
        self.assertNotIn("page=", s.api_url)

    def test_int_params_appear(self):
        fake = FakeResponse(status=200, data={})
        with patch.object(Endpoint, "http_get", return_value=fake):
            s = Search(q="x", page=3, page_size=50)
        self.assertIn("page=3", s.api_url)
        self.assertIn("page_size=50", s.api_url)

    def test_all_none_yields_empty_query(self):
        fake = FakeResponse(status=200, data={})
        with patch.object(Endpoint, "http_get", return_value=fake):
            s = Search()
        self.assertEqual(s.api_url, f"{NASA_SEARCH_ENDPOINT}?")

    def test_url_encodes_special_chars(self):
        fake = FakeResponse(status=200, data={})
        with patch.object(Endpoint, "http_get", return_value=fake):
            s = Search(q="moon landing")
        self.assertIn("q=moon+landing", s.api_url)
