import json
import tempfile
import unittest
from pathlib import Path

from gallery import (
    _MONTH_GALLERY_THRESHOLD,
    _YEAR_GALLERY_THRESHOLD,
    generate,
    load_metadata,
    render_breadcrumb,
    render_card,
    scan_nasa_id_dir,
    write_day_gallery,
    write_month_index,
    write_unknown_gallery,
    write_year_index,
)


def _make_nasa_dir(parent: Path, nasa_id: str, ext: str = "jpg", meta: dict | None = None) -> Path:
    d = parent / nasa_id
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{nasa_id}~orig.{ext}").write_bytes(b"fake")
    (d / "metadata.json").write_text(
        json.dumps(meta or {"AVAIL:Title": f"Title for {nasa_id}"}),
        encoding="utf-8",
    )
    return d


class TestLoadMetadata(unittest.TestCase):
    def test_reads_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "id1"
            d.mkdir()
            (d / "metadata.json").write_text(
                json.dumps({"AVAIL:Title": "Moon", "AVAIL:Center": "JSC"}),
                encoding="utf-8",
            )
            meta = load_metadata(d)
            self.assertEqual(meta["AVAIL:Title"], "Moon")
            self.assertEqual(meta["AVAIL:Center"], "JSC")

    def test_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "id1"
            d.mkdir()
            self.assertEqual(load_metadata(d), {})

    def test_invalid_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "id1"
            d.mkdir()
            (d / "metadata.json").write_text("not json", encoding="utf-8")
            self.assertEqual(load_metadata(d), {})


class TestScanNasaIdDir(unittest.TestCase):
    def test_jpg_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_nasa_dir(
                Path(tmp),
                "ABC-123",
                ext="jpg",
                meta={
                    "AVAIL:Title": "Rocket Launch",
                    "AVAIL:Description": "A big rocket.",
                    "AVAIL:DateCreated": "2024-01-02",
                    "AVAIL:Center": "KSC",
                    "AVAIL:Keywords": ["rocket", "launch"],
                },
            )
            item = scan_nasa_id_dir(d)
            self.assertEqual(item["nasa_id"], "ABC-123")
            self.assertEqual(item["orig_file"], "ABC-123~orig.jpg")
            self.assertEqual(item["ext"], "jpg")
            self.assertEqual(item["title"], "Rocket Launch")
            self.assertEqual(item["center"], "KSC")
            self.assertEqual(item["keywords"], ["rocket", "launch"])
            self.assertFalse(item["is_tif"])
            self.assertFalse(item["is_video"])
            self.assertFalse(item["is_audio"])

    def test_tif_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_nasa_dir(Path(tmp), "old-scan", ext="tif")
            item = scan_nasa_id_dir(d)
            self.assertTrue(item["is_tif"])

    def test_part_file_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "id1"
            d.mkdir()
            (d / "id1~orig.jpg.part").write_bytes(b"incomplete")
            (d / "metadata.json").write_text("{}", encoding="utf-8")
            item = scan_nasa_id_dir(d)
            self.assertIsNone(item["orig_file"])

    def test_missing_orig_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "id1"
            d.mkdir()
            (d / "metadata.json").write_text("{}", encoding="utf-8")
            item = scan_nasa_id_dir(d)
            self.assertIsNone(item["orig_file"])

    def test_keywords_non_list_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_nasa_dir(
                Path(tmp), "id1", meta={"AVAIL:Keywords": "not-a-list"}
            )
            item = scan_nasa_id_dir(d)
            self.assertEqual(item["keywords"], [])


class TestRenderBreadcrumb(unittest.TestCase):
    def test_last_item_is_span(self):
        html = render_breadcrumb([("Catalog", "../index.html"), ("2024", "")])
        self.assertIn('<a href="../index.html">Catalog</a>', html)
        self.assertIn("<span>2024</span>", html)

    def test_empty_returns_empty_string(self):
        self.assertEqual(render_breadcrumb([]), "")

    def test_escapes_special_chars(self):
        html = render_breadcrumb([("A&B", "x.html"), ("C<D>", "")])
        self.assertIn("A&amp;B", html)
        self.assertIn("C&lt;D&gt;", html)


class TestRenderCard(unittest.TestCase):
    def _item(self, **kwargs):
        defaults = {
            "nasa_id": "id1",
            "rel_dir": "id1",
            "orig_file": "id1~orig.jpg",
            "ext": "jpg",
            "title": "Test Image",
            "description": "",
            "description_508": "Alt text",
            "date_created": "2024-01-02",
            "center": "KSC",
            "keywords": [],
            "is_tif": False,
            "is_video": False,
            "is_audio": False,
        }
        defaults.update(kwargs)
        return defaults

    def test_jpg_has_img_tag(self):
        html = render_card(self._item())
        self.assertIn("<img ", html)
        self.assertIn('src="id1/id1~orig.jpg"', html)

    def test_tif_no_img_tag(self):
        html = render_card(self._item(orig_file="id1~orig.tif", ext="tif", is_tif=True))
        self.assertNotIn("<img ", html)
        self.assertIn("download", html)
        self.assertIn("TIFF", html)

    def test_missing_file_shows_note(self):
        html = render_card(self._item(orig_file=None))
        self.assertNotIn("<img ", html)
        self.assertIn("not available", html)

    def test_long_description_truncated(self):
        long_desc = "x" * 400
        html = render_card(self._item(description=long_desc))
        self.assertIn("...", html)
        self.assertIn("<details>", html)

    def test_short_description_no_details(self):
        html = render_card(self._item(description="Short desc"))
        self.assertNotIn("<details>", html)
        self.assertIn("Short desc", html)

    def test_keywords_rendered(self):
        html = render_card(self._item(keywords=["moon", "landing"]))
        self.assertIn("moon", html)
        self.assertIn("landing", html)

    def test_title_escaped(self):
        html = render_card(self._item(title="A & B"))
        self.assertIn("A &amp; B", html)


class TestWriteDayGallery(unittest.TestCase):
    def test_creates_index_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            day_dir = root / "2024" / "01" / "2024-01-02"
            day_dir.mkdir(parents=True)
            _make_nasa_dir(day_dir, "id-1")
            _make_nasa_dir(day_dir, "id-2")
            count = write_day_gallery(day_dir)
            self.assertEqual(count, 2)
            index = day_dir / "index.html"
            self.assertTrue(index.exists())
            content = index.read_text(encoding="utf-8")
            self.assertIn("<img ", content)
            self.assertIn("id-1", content)
            self.assertIn("id-2", content)
            # Breadcrumb should link up to catalog root
            self.assertIn("../../../index.html", content)

    def test_tif_item_no_img_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            day_dir = root / "1969" / "07" / "1969-07-24"
            day_dir.mkdir(parents=True)
            _make_nasa_dir(day_dir, "scan-1", ext="tif")
            write_day_gallery(day_dir)
            content = (day_dir / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("<img ", content)
            self.assertIn("TIFF", content)


class TestWriteMonthIndex(unittest.TestCase):
    def _month_dir(self, root: Path, year: str, month: str) -> Path:
        d = root / year / month
        d.mkdir(parents=True)
        return d

    def test_small_month_writes_gallery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            month_dir = self._month_dir(root, "2024", "03")
            day_dir = month_dir / "2024-03-01"
            day_dir.mkdir()
            _make_nasa_dir(day_dir, "img-1")
            _make_nasa_dir(day_dir, "img-2")
            count = write_month_index(month_dir)
            self.assertEqual(count, 2)
            content = (month_dir / "index.html").read_text(encoding="utf-8")
            # Should be a gallery page (contains img tags), not an index
            self.assertIn("<img ", content)
            self.assertIn("img-1", content)
            # No day-level index.html written
            self.assertFalse((day_dir / "index.html").exists())

    def test_large_month_writes_day_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            month_dir = self._month_dir(root, "2024", "06")
            # Create enough items to exceed the threshold
            for i in range(_MONTH_GALLERY_THRESHOLD):
                day_dir = month_dir / f"2024-06-{(i % 28) + 1:02d}"
                day_dir.mkdir(exist_ok=True)
                _make_nasa_dir(day_dir, f"img-{i:04d}")
            count = write_month_index(month_dir)
            self.assertEqual(count, _MONTH_GALLERY_THRESHOLD)
            content = (month_dir / "index.html").read_text(encoding="utf-8")
            # Should be an index page (links to day subdirs, not a gallery)
            self.assertIn("index.html", content)
            self.assertNotIn("<img ", content)
            # Day-level index.html files should exist
            for day_dir in month_dir.iterdir():
                if day_dir.is_dir():
                    self.assertTrue((day_dir / "index.html").exists())


class TestWriteYearIndex(unittest.TestCase):
    def test_small_year_writes_gallery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            year_dir = root / "2024"
            month_dir = year_dir / "03"
            day_dir = month_dir / "2024-03-01"
            day_dir.mkdir(parents=True)
            _make_nasa_dir(day_dir, "img-1")
            count = write_year_index(year_dir)
            self.assertEqual(count, 1)
            content = (year_dir / "index.html").read_text(encoding="utf-8")
            # Should be a gallery page with images, not a list of months
            self.assertIn("<img ", content)
            self.assertIn("img-1", content)
            # Month and day sub-pages should NOT be written
            self.assertFalse((month_dir / "index.html").exists())
            self.assertFalse((day_dir / "index.html").exists())

    def test_large_year_writes_month_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            year_dir = root / "2024"
            # Spread items across two months to exceed the threshold
            for month, start in (("01", 0), ("02", _YEAR_GALLERY_THRESHOLD // 2)):
                month_dir = year_dir / month
                day_dir = month_dir / f"2024-{month}-01"
                day_dir.mkdir(parents=True)
                for i in range(_YEAR_GALLERY_THRESHOLD):
                    _make_nasa_dir(day_dir, f"img-{start + i:04d}")
            count = write_year_index(year_dir)
            self.assertGreaterEqual(count, _YEAR_GALLERY_THRESHOLD)
            content = (year_dir / "index.html").read_text(encoding="utf-8")
            # Should be an index page, not a gallery
            self.assertNotIn("<img ", content)
            self.assertIn("01/index.html", content)
            self.assertIn("02/index.html", content)

    def test_small_year_rel_dir_correct(self):
        """Images in the year gallery should have src paths relative to the year dir."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            year_dir = root / "2024"
            day_dir = year_dir / "05" / "2024-05-10"
            day_dir.mkdir(parents=True)
            _make_nasa_dir(day_dir, "abc-123")
            write_year_index(year_dir)
            content = (year_dir / "index.html").read_text(encoding="utf-8")
            self.assertIn("05/2024-05-10/abc-123/", content)


class TestWriteUnknownGallery(unittest.TestCase):
    def test_creates_index_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unknown_dir = root / "unknown"
            unknown_dir.mkdir()
            _make_nasa_dir(unknown_dir, "mystery-1")
            count = write_unknown_gallery(unknown_dir)
            self.assertEqual(count, 1)
            index = unknown_dir / "index.html"
            self.assertTrue(index.exists())
            content = index.read_text(encoding="utf-8")
            self.assertIn("Unknown Date", content)
            self.assertIn("mystery-1", content)
            self.assertIn("../index.html", content)


class TestGenerate(unittest.TestCase):
    def _build_catalog(self, root: Path) -> None:
        day1 = root / "2024" / "01" / "2024-01-02"
        day1.mkdir(parents=True)
        _make_nasa_dir(day1, "id-jpg", ext="jpg")
        _make_nasa_dir(day1, "id-tif", ext="tif",
                       meta={"AVAIL:Title": "Old scan", "AVAIL:MediaType": "image"})

        unknown = root / "unknown"
        unknown.mkdir()
        _make_nasa_dir(unknown, "mystery-1")

    def test_index_files_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._build_catalog(root)
            n = generate(root)
            # 2 items total → below year threshold → only root, 2024/, unknown/ = 3
            self.assertEqual(n, 3)
            for path in [
                root / "index.html",
                root / "2024" / "index.html",
                root / "unknown" / "index.html",
            ]:
                self.assertTrue(path.exists(), f"missing: {path}")
            # Month and day pages should NOT be written for a small year
            self.assertFalse((root / "2024" / "01" / "index.html").exists())
            self.assertFalse((root / "2024" / "01" / "2024-01-02" / "index.html").exists())

    def test_root_index_links_to_year_and_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._build_catalog(root)
            generate(root)
            content = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn("2024/index.html", content)
            self.assertIn("unknown/index.html", content)

    def test_no_unknown_dir_omitted_from_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            day1 = root / "2024" / "01" / "2024-01-02"
            day1.mkdir(parents=True)
            _make_nasa_dir(day1, "id-1")
            generate(root)
            content = (root / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("unknown", content)

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._build_catalog(root)
            generate(root)
            n2 = generate(root)
            self.assertEqual(n2, 3)


if __name__ == "__main__":
    unittest.main()
