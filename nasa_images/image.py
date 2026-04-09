import json
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

NASA_API_URL = "https://images-api.nasa.gov"
NASA_ASSET_ENDPOINT = f"{NASA_API_URL}/asset/"
NASA_DETAILS_URL = "https://images.nasa.gov/details/"


class Image:
    def __init__(self, nasa_id: str) -> None:
        self.nasa_id = nasa_id
        self.metadata_url = None
        self.original_url = None
        self.large_url = None
        self.medium_url = None
        self.small_url = None
        self.thumbnail_url = None
        self.found = self._fetch_assets()
        self.details_url = f"{NASA_DETAILS_URL}{self.nasa_id}"
        self._metadata = None

    def download_image(
        self, file: str | None = None, dir: str | None = None
    ) -> Path | None:
        if not self.original_url:
            return None
        suffix = Path(urllib.parse.urlparse(self.original_url).path).suffix
        filename = Path(file) if file else Path(f"{self.nasa_id}~orig{suffix}")
        dest = (Path(dir) if dir else Path(".")) / filename
        urllib.request.urlretrieve(self.original_url, dest)
        return dest

    def write_metadata(self, file: str | None = None, dir: str | None = None) -> None:
        file = Path(f"{self.nasa_id}~metadata.json") if not file else Path(file)
        dir = Path(".") if not dir else Path(dir)
        path = dir / file
        with open(path, "w") as f:
            json.dump(self.metadata, f, indent=4)

    @property
    def datetime(self) -> datetime | None:
        meta = self.metadata
        if not meta:
            return None

        # EXIF:CreateDate + EXIF:OffsetTime
        if dt_str := meta.get("EXIF:CreateDate"):
            return self._parse_exif_datetime(dt_str, meta.get("EXIF:OffsetTime"))

        # EXIF:DateTimeOriginal + EXIF:OffsetTime
        if dt_str := meta.get("EXIF:DateTimeOriginal"):
            return self._parse_exif_datetime(dt_str, meta.get("EXIF:OffsetTime"))

        # IPTC:DateCreated + IPTC:TimeCreated
        if date_str := meta.get("IPTC:DateCreated"):
            time_str = meta.get("IPTC:TimeCreated", "00:00:00")
            combined = f"{date_str} {time_str}"
            # IPTC:TimeCreated may include offset like "15:51:37-05:00"
            try:
                return datetime.strptime(combined, "%Y:%m:%d %H:%M:%S%z")
            except ValueError:
                try:
                    return datetime.strptime(combined, "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    pass

        # AVAIL:DateCreated (ISO format)
        if avail_str := meta.get("AVAIL:DateCreated"):
            try:
                return datetime.fromisoformat(avail_str)
            except ValueError:
                pass

        return None

    @staticmethod
    def _parse_exif_datetime(
        dt_str: str, offset_str: str | None = None
    ) -> datetime | None:
        try:
            dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            return None
        if offset_str:
            try:
                offset_dt = datetime.strptime(offset_str, "%z")
                dt = dt.replace(tzinfo=offset_dt.tzinfo)
            except ValueError:
                pass
        return dt

    @property
    def metadata(self) -> dict[str, Any]:
        if not self._metadata:
            self._metadata = self._fetch_json(self.metadata_url)
        return self._metadata

    def _fetch_assets(self) -> bool:
        encoded_id = urllib.parse.quote(self.nasa_id)
        assets = self._fetch_json(f"{NASA_ASSET_ENDPOINT}{encoded_id}")
        if assets and "collection" in assets:
            items = assets.get("collection").get("items")
            if items:
                for item in items:
                    href = item.get("href", "")
                    if "~orig." in href:
                        self.original_url = href.replace(" ", "%20")
                    elif "~large." in href:
                        self.large_url = href.replace(" ", "%20")
                    elif "~medium." in href:
                        self.medium_url = href.replace(" ", "%20")
                    elif "~small." in href:
                        self.small_url = href.replace(" ", "%20")
                    elif "~thumb." in href:
                        self.thumbnail_url = href.replace(" ", "%20")
                    elif href.endswith("/metadata.json"):
                        self.metadata_url = href.replace(" ", "%20")
                return True
        return False

    def _fetch_json(self, url: str) -> dict[str, Any]:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read())
