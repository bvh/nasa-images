from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
import urllib.parse
import urllib.request

NASA_DETAILS_URL = "https://images.nasa.gov/details/"
NASA_API_URL = "https://images-api.nasa.gov"
NASA_ASSET_ENDPOINT = f"{NASA_API_URL}/asset/"


class Response:
    def __init__(self, response: urllib.request.HTTPResponse) -> None:
        self._response = response
        self._status = response.getcode()
        self._bytes = response.read()
        self._encoding = response.headers.get_content_charset() or "utf-8"

    @property
    def status(self) -> int:
        return self._status

    @property
    def text(self) -> str:
        return self._bytes.decode(self._encoding)

    def parse_json(self) -> dict[str, Any]:
        if self.status == 200:
            return json.loads(self.text)
        else:
            return {}


class Endpoint:
    @staticmethod
    def http_get(url: str) -> urllib.request.HTTPResponse | None:
        if url and len(url):
            try:
                with urllib.request.urlopen(url) as response:
                    return Response(response)
            except HTTPError as e:
                print(f"HTTP Error: {e.code} - {e.reason}", file=sys.stderr)
            except URLError as e:
                print(f"URL Error: {e.reason}", file=sys.stderr)
        return None

    @staticmethod
    def collapse_items(items: list[dict[str, str]], key: str = "href") -> list[str]:
        result = []
        for item in items:
            result.append(item.get(key))
        return result


class Asset(Endpoint):
    def __init__(self, nasa_id: str) -> None:
        self.nasa_id = nasa_id
        self.encoded_id = urllib.parse.quote(urllib.parse.unquote(self.nasa_id))
        self.url = f"{NASA_ASSET_ENDPOINT}{self.encoded_id}"
        self.response = self.http_get(self.url)
        self.manifest = self.response.parse_json()
        self.collection = self.manifest.get("collection", {})
        self.href = self.collection.get("href", "")
        self.items = self.collapse_items(self.collection.get("items", []), key="href")
        self.okay = True if self.response.status == 200 else False
        self.details_url = f"{NASA_DETAILS_URL}{self.nasa_id}"
        self._metadata = None

    def find_url(self, tag: str) -> str | None:
        # special case for metadata tag
        if tag.lower() == "metadata":
            for item in self.items:
                if item.endswith("/metadata.json"):
                    return item.replace(" ", "%20")
        else:
            search_key = f"~{tag}."
            for item in self.items:
                if search_key in item:
                    return item.replace(" ", "%20")
        return None

    @property
    def metadata(self) -> dict[str, Any]:
        if not self._metadata:
            metadata = {}
            url = self.find_url("metadata")
            if url:
                response = self.http_get(url)
                if response.status == 200:
                    metadata = response.parse_json()
            else:
                print("WARNING: metadata not found")
            self._metadata = metadata
        return self._metadata

    def write_metadata(self, path: Path | None = None) -> None:
        path = Path(f"{self.nasa_id}~metadata.json") if not path else path
        path.write_text(json.dumps(self.metadata, indent=4))

    def download(self, tag: str, target: Path | None = None) -> None:
        url = self.find_url(tag)
        if url:
            suffix = Path(urllib.parse.urlparse(url).path).suffix
            if target:
                target = target.with_suffix(suffix)
            else:
                target = Path(f"{self.nasa_id}~{tag}{suffix}")
            urllib.request.urlretrieve(url, target)
        else:
            print(f"WARNING: item not found ({self.nasa_id}~{tag})")
        return

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
