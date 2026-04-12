# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```sh
uv run nasa.py call asset --id <nasa_id>
uv run nasa.py call metadata --id <nasa_id>
uv run nasa.py call album --album <album_name> [--page <page>]
uv run nasa.py call captions --id <nasa_id>
uv run nasa.py call search [--q TEXT] [--center TEXT] [--description TEXT] [--keywords TEXT] \
  [--location TEXT] [--media-type TEXT] [--nasa-id TEXT] [--page INT] [--page-size INT] \
  [--photographer TEXT] [--secondary-creator TEXT] [--title TEXT] [--year-start YYYY] [--year-end YYYY]
uv run nasa.py fetch media --id <nasa_id> [--catalog <dir>]
uv run nasa.py fetch album --album <album_name> [--media-type image|video|audio] [--catalog <dir>]
uv run nasa.py fetch search [--q TEXT] [--center TEXT] [--description TEXT] \
  [--keywords TEXT] [--location TEXT] [--media-type TEXT] [--nasa-id TEXT] \
  [--page-size INT] [--photographer TEXT] [--secondary-creator TEXT] \
  [--title TEXT] [--year-start YYYY] [--year-end YYYY] [--catalog <dir>]

# Example
uv run nasa.py call asset --id art002e000192
uv run nasa.py call search --q "moon landing" --media-type image --page-size 5
uv run nasa.py fetch media --id art002e000192 --catalog /tmp/nasa-cat
uv run nasa.py fetch album --album Artemis_II --media-type image --catalog /tmp/nasa-cat
```

## Testing

```sh
uv run python -m unittest discover tests
```

Tests live under `tests/` and use `unittest` + `unittest.mock.patch` (stdlib only — no dev dependencies). Network calls are mocked via `FakeResponse` in `tests/fixtures.py`; the suite never hits the live NASA API. There is no linter configuration at this time.

The `test_empty_dirs_should_not_appear` case in `tests/test_inventory.py` is marked `@unittest.expectedFailure` to track a known bug in `inventory.py:19` where empty directories are misclassified as leaf `nasa_id` dirs.

## Architecture

`nasa.py` is a thin top-level entry point that calls `nasa_images.__main__.main()`.

`nasa_images/api.py` contains six classes:
- `Response` — wraps `urllib.request.HTTPResponse`; exposes `.status`, `.text`, and `.parse_json()`.
- `Endpoint` — base class with `http_get()` (static method; wraps `urllib.request.urlopen`, returns a `Response`) and `collapse_items()` (flattens a list of dicts to a list of values for a given key). `http_get()` can be called directly as `Endpoint.http_get(url)` without instantiating a subclass.
- `Asset(Endpoint)` — wraps `/asset/{nasa_id}`.
- `Metadata(Endpoint)` — wraps `/metadata/{nasa_id}`.
- `Album(Endpoint)` — wraps `/album/{album_name}` with an optional `?page=` query parameter.
- `Captions(Endpoint)` — wraps `/captions/{nasa_id}`.
- `Search(Endpoint)` — wraps `/search`; builds the query string from up to 15 optional parameters via `urllib.parse.urlencode()`.

All endpoint classes follow the same construction pattern: encode params → build `self.api_url` → call `http_get()` → check status into `self.okay` → call `parse_json()` → store in `self.data`.

`nasa_images/__main__.py` provides the CLI via `argparse`. The first positional argument is `operation` (`call` or `fetch`); the second is `operand`. `call <endpoint>` dispatches on `asset`, `metadata`, `album`, `captions`, or `search` and prints the raw JSON response. `fetch media --id <nasa_id> [--catalog <dir>]` downloads the canonical `~orig` asset and its `metadata.json` into a date-partitioned catalog (`<catalog>/<YYYY>/<MM>/<YYYY-MM-DD>/<nasa_id>/`, or `<catalog>/unknown/<nasa_id>/` when no usable date is found). Existing files are never overwritten — a warning is printed and the file is skipped. `fetch album --album <name> [--media-type image] [--catalog <dir>]` walks every page of an album (following `rel: "next"` pagination links), optionally filters by `media_type`, and calls `fetch_media_by_id` for each matching item. `fetch search [--q TEXT] [...]` does the same for search results — all search parameters are forwarded to the API as server-side filters; `media_type` filtering is not duplicated client-side. The catalog layout logic lives in `nasa_images/fetch.py`.

`nasa_images/fetch.py` maintains a `catalog.txt` index file at the catalog root (one `nasa_id` per line, kept sorted) to enable fast deduplication across runs without re-scanning the directory tree. Downloads use a `.part` temporary file that is atomically renamed on success and deleted on failure. Rate-limiting constants: `_DOWNLOAD_DELAY_SECS = 0.25` between assets, `_PAGE_DELAY_SECS = 0.5` between album pages — always preserve these delays when modifying loops that hit the NASA API.

`inventory.py` is a standalone utility (`python inventory.py <catalog>`) that scans a catalog directory and prints all `nasa_id`s found (leaf directories containing only files, no subdirectories).

The project has **no external dependencies** — stdlib only (`urllib`, `json`, `argparse`). Python 3.14+ is required. Package management uses `uv`.
