import json
import os
import re
import shutil
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from nasa_images.api import Album, Asset, Endpoint, Search

_DOWNLOAD_DELAY_SECS = 0.25   # pause between per-asset downloads
_PAGE_DELAY_SECS = 0.5        # pause between album page requests


_ORIG_RE = re.compile(r"~orig\.[^./]+$")


@dataclass(frozen=True)
class PartialDate:
    year: int
    month: int | None = None
    day: int | None = None


def fetch_media_by_id(
    nasa_id: str,
    catalog: Path,
    catalog_index: set[str] | None = None,
) -> bool:
    _own_index = catalog_index is None
    if _own_index:
        catalog_index = _load_catalog_index(catalog)

    if nasa_id in catalog_index:
        print(f"skipped {nasa_id} (already in catalog)")
        return True

    asset = Asset(nasa_id)
    if not asset.okay or not asset.data:
        print(f"ERROR: asset {nasa_id} not found", file=sys.stderr)
        return False

    orig_url, metadata_url = _asset_urls(asset.data)
    if not orig_url:
        print(f"WARNING: no ~orig file found for {nasa_id}; skipping", file=sys.stderr)
        return False

    meta: dict[str, Any] | None = None
    if metadata_url:
        meta = _load_metadata_json(metadata_url)
    if meta is None:
        print(f"WARNING: could not load metadata.json for {nasa_id}", file=sys.stderr)
        meta = {}

    d = _extract_date(meta)
    if d is None:
        print(f"WARNING: no usable date for {nasa_id}; filing under unknown/", file=sys.stderr)
    elif d.day is None:
        loc = f"{d.year:04d}/" if d.month is None else f"{d.year:04d}/{d.month:02d}/"
        print(f"WARNING: partial date for {nasa_id}; filing under {loc}unknown/", file=sys.stderr)

    dest_dir = _destination(catalog, nasa_id, d)
    dest_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = dest_dir / "metadata.json"
    if metadata_path.exists():
        print(f"WARNING: {metadata_path} already exists; skipping", file=sys.stderr)
    elif meta:
        _write_metadata(meta, metadata_path)

    orig_name = orig_url.rsplit("/", 1)[-1]
    orig_path = dest_dir / orig_name
    if orig_path.exists():
        print(f"WARNING: {orig_path} already exists; skipping", file=sys.stderr)
    else:
        _download_file(orig_url, orig_path)

    if not orig_path.exists():
        return False
    if metadata_url and not metadata_path.exists():
        return False

    catalog_index.add(nasa_id)
    if _own_index:
        _save_catalog_index(catalog, catalog_index)

    print(f"fetched {nasa_id} -> {dest_dir}")
    return True


def fetch_album_by_name(
    album_name: str,
    catalog: Path,
    media_type: str | None = None,
) -> None:
    page = 1
    total = 0
    fetched = 0
    skipped = 0

    catalog_index = _load_catalog_index(catalog)

    while True:
        album = Album(album_name, page=page)
        if not album.okay or not album.data:
            print(f"ERROR: failed to load album '{album_name}' page {page}", file=sys.stderr)
            break

        collection = album.data.get("collection") or {}
        items = collection.get("items") or []

        for item in items:
            item_data_list = item.get("data") or []
            if not item_data_list:
                continue
            item_data = item_data_list[0]

            item_media_type = item_data.get("media_type")
            if media_type is not None and item_media_type != media_type:
                continue

            nasa_id = item_data.get("nasa_id")
            if not nasa_id:
                print("WARNING: album item missing nasa_id; skipping", file=sys.stderr)
                continue

            total += 1
            already_present = nasa_id in catalog_index
            try:
                ok = fetch_media_by_id(nasa_id, catalog, catalog_index)
            except Exception as exc:
                print(f"ERROR: failed to fetch {nasa_id}: {exc}", file=sys.stderr)
                time.sleep(_DOWNLOAD_DELAY_SECS)
                continue
            if ok:
                if already_present:
                    skipped += 1
                else:
                    fetched += 1
                    _save_catalog_index(catalog, catalog_index)
            time.sleep(_DOWNLOAD_DELAY_SECS)

        links = collection.get("links") or []
        next_link = next((link for link in links if link.get("rel") == "next"), None)
        next_href = next_link.get("href") if next_link else None
        if next_href and next_href != album.api_url:
            page += 1
            time.sleep(_PAGE_DELAY_SECS)
        else:
            break

    print(f"fetched {fetched}, skipped {skipped} of {total} items from album '{album_name}'")


def fetch_search(
    catalog: Path,
    q: str | None = None,
    center: str | None = None,
    description: str | None = None,
    description_508: str | None = None,
    keywords: str | None = None,
    location: str | None = None,
    media_type: str | None = None,
    nasa_id: str | None = None,
    page_size: int | None = None,
    photographer: str | None = None,
    secondary_creator: str | None = None,
    title: str | None = None,
    year_start: str | None = None,
    year_end: str | None = None,
) -> None:
    page = 1
    total = 0
    fetched = 0
    skipped = 0

    catalog_index = _load_catalog_index(catalog)

    while True:
        results = Search(
            q=q,
            center=center,
            description=description,
            description_508=description_508,
            keywords=keywords,
            location=location,
            media_type=media_type,
            nasa_id=nasa_id,
            page=page,
            page_size=page_size,
            photographer=photographer,
            secondary_creator=secondary_creator,
            title=title,
            year_start=year_start,
            year_end=year_end,
        )
        if not results.okay or not results.data:
            print(f"ERROR: search failed on page {page}", file=sys.stderr)
            break

        collection = results.data.get("collection") or {}
        items = collection.get("items") or []

        for item in items:
            item_data_list = item.get("data") or []
            if not item_data_list:
                continue
            item_data = item_data_list[0]

            item_nasa_id = item_data.get("nasa_id")
            if not item_nasa_id:
                print("WARNING: search result item missing nasa_id; skipping", file=sys.stderr)
                continue

            total += 1
            already_present = item_nasa_id in catalog_index
            try:
                ok = fetch_media_by_id(item_nasa_id, catalog, catalog_index)
            except Exception as exc:
                print(f"ERROR: failed to fetch {item_nasa_id}: {exc}", file=sys.stderr)
                time.sleep(_DOWNLOAD_DELAY_SECS)
                continue
            if ok:
                if already_present:
                    skipped += 1
                else:
                    fetched += 1
                    _save_catalog_index(catalog, catalog_index)
            time.sleep(_DOWNLOAD_DELAY_SECS)

        links = collection.get("links") or []
        next_link = next((link for link in links if link.get("rel") == "next"), None)
        next_href = next_link.get("href") if next_link else None
        if next_href and next_href != results.api_url:
            page += 1
            time.sleep(_PAGE_DELAY_SECS)
        else:
            break

    print(f"fetched {fetched}, skipped {skipped} of {total} items from search")


def _asset_urls(asset_data: dict[str, Any]) -> tuple[str | None, str | None]:
    collection = asset_data.get("collection") or {}
    items = collection.get("items") or []
    hrefs = Endpoint.collapse_items(items, key="href")

    orig_url: str | None = None
    metadata_url: str | None = None
    for href in hrefs:
        if not href:
            continue
        basename = href.rsplit("/", 1)[-1]
        if orig_url is None and _ORIG_RE.search(basename):
            orig_url = href
        elif metadata_url is None and basename == "metadata.json":
            metadata_url = href
    return orig_url, metadata_url


def _load_metadata_json(metadata_url: str) -> dict[str, Any] | None:
    response = Endpoint.http_get(metadata_url)
    if response is None or response.status != 200:
        return None
    return response.parse_json()


def _extract_date(meta: dict[str, Any]) -> PartialDate | None:
    # Each entry: (format_string, has_month, has_day)
    exif_specs: tuple[tuple[str, bool, bool], ...] = (
        ("%Y:%m:%d %H:%M:%S", True, True),
    )
    avail_specs: tuple[tuple[str, bool, bool], ...] = (
        ("%Y-%m-%dT%H:%M:%SZ", True, True),       # "2022-03-04T05:06:07Z"
        ("%Y-%m-%dT%H:%M:%S%z", True, True),       # "1969-03-09T00:00:00-08:00"
        ("%Y-%m-%d", True, True),                   # "2021-07-08"
        ("%Y:%m:%d", True, True),                   # "2020:11:12"
        ("%d %B %Y", True, True),                   # "05 December 2022"
        ("%Y-%m", True, False),                     # "2019-06"
        ("%Y", False, False),                       # "2019"
    )

    candidates: list[tuple[Any, tuple[tuple[str, bool, bool], ...]]] = [
        (meta.get("EXIF:DateTimeOriginal"), exif_specs),
        (meta.get("EXIF:CreateDate"), exif_specs),
        (meta.get("AVAIL:DateCreated"), avail_specs),
    ]
    for value, specs in candidates:
        if not isinstance(value, str) or not value:
            continue
        for fmt, has_month, has_day in specs:
            try:
                dt = datetime.strptime(value, fmt)
            except ValueError:
                continue
            if has_day:
                return PartialDate(dt.year, dt.month, dt.day)
            if has_month:
                return PartialDate(dt.year, dt.month)
            return PartialDate(dt.year)
    return None


def _destination(catalog: Path, nasa_id: str, d: PartialDate | None) -> Path:
    if d is None:
        return catalog / "unknown" / nasa_id
    if d.day is not None:
        day_str = f"{d.year:04d}-{d.month:02d}-{d.day:02d}"
        return catalog / f"{d.year:04d}" / f"{d.month:02d}" / day_str / nasa_id
    if d.month is not None:
        return catalog / f"{d.year:04d}" / f"{d.month:02d}" / "unknown" / nasa_id
    return catalog / f"{d.year:04d}" / "unknown" / nasa_id


def _write_metadata(meta: dict[str, Any], dest: Path) -> None:
    with dest.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=4)


def _download_file(url: str, dest: Path) -> None:
    part = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(url.replace(" ", "%20")) as response, part.open("wb") as out:
            shutil.copyfileobj(response, out)
        os.replace(part, dest)
    except Exception:
        if part.exists():
            part.unlink()
        raise


def _catalog_index_path(catalog: Path) -> Path:
    return catalog / "catalog.txt"


def _load_catalog_index(catalog: Path) -> set[str]:
    p = _catalog_index_path(catalog)
    if not p.exists():
        return set()
    return set(p.read_text(encoding="utf-8").splitlines())


def _save_catalog_index(catalog: Path, ids: set[str]) -> None:
    _catalog_index_path(catalog).write_text(
        "\n".join(sorted(ids)) + "\n", encoding="utf-8"
    )
