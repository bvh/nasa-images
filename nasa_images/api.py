import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
import urllib.parse
import urllib.request

NASA_DETAILS_URL = "https://images.nasa.gov/details/"
NASA_API_URL = "https://images-api.nasa.gov"
NASA_ASSET_ENDPOINT = f"{NASA_API_URL}/asset/"
NASA_METADATA_ENDPOINT = f"{NASA_API_URL}/metadata/"
NASA_ALBUM_ENDPOINT = f"{NASA_API_URL}/album/"
NASA_CAPTIONS_ENDPOINT = f"{NASA_API_URL}/captions/"
NASA_SEARCH_ENDPOINT = f"{NASA_API_URL}/search"


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
                with urllib.request.urlopen(url.replace(" ", "%20")) as response:
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

    def _fetch(self) -> None:
        self.response = self.http_get(self.api_url)
        self.okay = bool(self.response and self.response.status == 200)
        self.data = self.response.parse_json() if self.okay else None


class Asset(Endpoint):
    def __init__(self, nasa_id: str) -> None:
        self.nasa_id = nasa_id
        self.api_url = f"{NASA_ASSET_ENDPOINT}{urllib.parse.quote(urllib.parse.unquote(nasa_id))}"
        self._fetch()


class Metadata(Endpoint):
    def __init__(self, nasa_id: str) -> None:
        self.nasa_id = nasa_id
        self.api_url = f"{NASA_METADATA_ENDPOINT}{urllib.parse.quote(urllib.parse.unquote(nasa_id))}"
        self._fetch()


class Album(Endpoint):
    def __init__(self, album_name: str, page: int | None = None) -> None:
        self.album_name = album_name
        self.api_url = f"{NASA_ALBUM_ENDPOINT}{urllib.parse.quote(urllib.parse.unquote(album_name))}"
        if page is not None:
            self.api_url += f"?page={page}"
        self._fetch()


class Captions(Endpoint):
    def __init__(self, nasa_id: str) -> None:
        self.nasa_id = nasa_id
        self.api_url = f"{NASA_CAPTIONS_ENDPOINT}{urllib.parse.quote(urllib.parse.unquote(nasa_id))}"
        self._fetch()


class Search(Endpoint):
    def __init__(
        self,
        q: str | None = None,
        center: str | None = None,
        description: str | None = None,
        description_508: str | None = None,
        keywords: str | None = None,
        location: str | None = None,
        media_type: str | None = None,
        nasa_id: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        photographer: str | None = None,
        secondary_creator: str | None = None,
        title: str | None = None,
        year_start: str | None = None,
        year_end: str | None = None,
    ) -> None:
        params = {k: v for k, v in {
            "q": q,
            "center": center,
            "description": description,
            "description_508": description_508,
            "keywords": keywords,
            "location": location,
            "media_type": media_type,
            "nasa_id": nasa_id,
            "page": page,
            "page_size": page_size,
            "photographer": photographer,
            "secondary_creator": secondary_creator,
            "title": title,
            "year_start": year_start,
            "year_end": year_end,
        }.items() if v is not None}

        query_string = urllib.parse.urlencode(params)
        self.api_url = f"{NASA_SEARCH_ENDPOINT}?{query_string}"
        self._fetch()

