import json
import os
import re
import shutil
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any

from nasa_images.api import Asset, Endpoint


_ORIG_RE = re.compile(r"~orig\.[^./]+$")


def fetch_media_by_id(nasa_id: str, catalog: Path) -> bool:
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

    print(f"fetched {nasa_id} -> {dest_dir}")
    return True


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


def _extract_date(meta: dict[str, Any]) -> date | None:
    exif_formats = ("%Y:%m:%d %H:%M:%S",)
    avail_formats = ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y:%m:%d")

    candidates: list[tuple[Any, tuple[str, ...]]] = [
        (meta.get("EXIF:DateTimeOriginal"), exif_formats),
        (meta.get("EXIF:CreateDate"), exif_formats),
        (meta.get("AVAIL:DateCreated"), avail_formats),
    ]
    for value, formats in candidates:
        if not isinstance(value, str) or not value:
            continue
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _destination(catalog: Path, nasa_id: str, d: date | None) -> Path:
    if d is None:
        return catalog / "unknown" / nasa_id
    return catalog / f"{d.year:04d}" / f"{d.month:02d}" / d.isoformat() / nasa_id


def _write_metadata(meta: dict[str, Any], dest: Path) -> None:
    with dest.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=4)


def _download_file(url: str, dest: Path) -> None:
    part = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(url) as response, part.open("wb") as out:
            shutil.copyfileobj(response, out)
        os.replace(part, dest)
    except Exception:
        if part.exists():
            part.unlink()
        raise
