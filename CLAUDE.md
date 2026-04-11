# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```sh
# Run the CLI
uv run nasa.py call asset --id <nasa_id>

# Example
uv run nasa.py call asset --id art002e000192
```

There are no tests or linter configuration at this time.

## Architecture

`nasa.py` is a thin top-level entry point that calls `nasa_images.__main__.main()`.

`nasa_images/api.py` contains two classes:
- `Endpoint` — base class with `http_get()` (wraps `urllib.request.urlopen`, returns a `Response`) and `collapse_items()` (flattens a list of dicts to a list of values for a given key).
- `Asset(Endpoint)` — wraps the `/asset/{nasa_id}` endpoint. On construction it fetches the asset manifest and stores parsed JSON in `self.data`.

`nasa_images/__main__.py` provides the CLI via `argparse`. Currently supports one command: `call asset --id <nasa_id>`, which instantiates `Asset` and prints `self.data` as formatted JSON.

The project has **no external dependencies** — stdlib only (`urllib`, `json`, `argparse`). Python 3.14+ is required. Package management uses `uv`.
