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

# Example
uv run nasa.py call asset --id art002e000192
uv run nasa.py call search --q "moon landing" --media-type image --page-size 5
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

`nasa_images/__main__.py` provides the CLI via `argparse`. Commands are dispatched by the `operand` positional argument (`asset`, `metadata`, `album`, `captions`, `search`), each calling its corresponding handler function that instantiates the matching endpoint class and prints `self.data` as formatted JSON.

The project has **no external dependencies** — stdlib only (`urllib`, `json`, `argparse`). Python 3.14+ is required. Package management uses `uv`.
