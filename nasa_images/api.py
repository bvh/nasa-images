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
        self.api_url = f"{NASA_ASSET_ENDPOINT}{self.encoded_id}"

        self.response = self.http_get(self.api_url)
        self.okay = True if self.response and self.response.status == 200 else False
        if self.okay:
            self.data = self.response.parse_json()
        else:
            self.data = None


class Metadata(Endpoint):
    def __init__(self, nasa_id: str) -> None:
        self.nasa_id = nasa_id
        self.encoded_id = urllib.parse.quote(urllib.parse.unquote(self.nasa_id))
        self.api_url = f"{NASA_METADATA_ENDPOINT}{self.encoded_id}"

        self.response = self.http_get(self.api_url)
        self.okay = True if self.response and self.response.status == 200 else False
        if self.okay:
            self.data = self.response.parse_json()
        else:
            self.data = None

