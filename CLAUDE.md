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

# Example
uv run nasa.py call asset --id art002e000192
uv run nasa.py call search --q "moon landing" --media-type image --page-size 5
uv run nasa.py fetch media --id art002e000192 --catalog /tmp/nasa-cat
```

There are no tests or linter configuration at this time.

## Architecture

`nasa.py` is a thin top-level entry point that calls `nasa_images.__main__.main()`.

`nasa_images/api.py` contains six classes:
- `Response` — wraps `urllib.request.HTTPResponse`; exposes `.status`, `.text`, and `.parse_json()`.
- `Endpoint` — base class with `http_get()` (wraps `urllib.request.urlopen`, returns a `Response`) and `collapse_items()` (flattens a list of dicts to a list of values for a given key).
- `Asset(Endpoint)` — wraps `/asset/{nasa_id}`.
- `Metadata(Endpoint)` — wraps `/metadata/{nasa_id}`.
- `Album(Endpoint)` — wraps `/album/{album_name}` with an optional `?page=` query parameter.
- `Captions(Endpoint)` — wraps `/captions/{nasa_id}`.
- `Search(Endpoint)` — wraps `/search`; builds the query string from up to 15 optional parameters via `urllib.parse.urlencode()`.

All endpoint classes follow the same construction pattern: encode params → build `self.api_url` → call `http_get()` → check status into `self.okay` → call `parse_json()` → store in `self.data`.

`nasa_images/__main__.py` provides the CLI via `argparse`. The first positional argument is `operation` (`call` or `fetch`); the second is `operand`. `call <endpoint>` dispatches on `asset`, `metadata`, `album`, `captions`, or `search` and prints the raw JSON response. `fetch media --id <nasa_id> [--catalog <dir>]` downloads the canonical `~orig` asset and its `metadata.json` into a date-partitioned catalog (`<catalog>/<YYYY>/<MM>/<YYYY-MM-DD>/<nasa_id>/`, or `<catalog>/unknown/<nasa_id>/` when no usable date is found). Existing files are never overwritten — a warning is printed and the file is skipped. The catalog layout logic lives in `nasa_images/fetch.py`.

The project has **no external dependencies** — stdlib only (`urllib`, `json`, `argparse`). Python 3.14+ is required. Package management uses `uv`.
