import json
from typing import Any


class FakeResponse:
    def __init__(self, status: int = 200, data: Any = None, text: str | None = None) -> None:
        self._status = status
        self._data = data if data is not None else {}
        self._text = text if text is not None else json.dumps(self._data)

    @property
    def status(self) -> int:
        return self._status

    @property
    def text(self) -> str:
        return self._text

    def parse_json(self) -> dict[str, Any]:
        if self._status == 200:
            if isinstance(self._data, dict):
                return self._data
            return json.loads(self._text)
        return {}
