# NASA Images

A Python CLI for working with the NASA Image and Video Library API.

## Usage

```sh
# Query API endpoints (prints raw JSON)
uv run nasa.py call asset --id <nasa_id>
uv run nasa.py call metadata --id <nasa_id>
uv run nasa.py call captions --id <nasa_id>
uv run nasa.py call album --album <album_name> [--page <page>]
uv run nasa.py call search [--q TEXT] [--center TEXT] [--description TEXT] \
  [--description-508 TEXT] [--keywords TEXT] [--location TEXT] \
  [--media-type image|video|audio] [--nasa-id TEXT] [--page INT] \
  [--page-size INT] [--photographer TEXT] [--secondary-creator TEXT] \
  [--title TEXT] [--year-start YYYY] [--year-end YYYY]

# Download media to a local catalog
uv run nasa.py fetch media --id <nasa_id> [--catalog <dir>]
uv run nasa.py fetch album --album <album_name> [--media-type image|video|audio] [--catalog <dir>]
```

### Examples

```sh
uv run nasa.py call asset --id art002e000192
uv run nasa.py call search --q "moon landing" --media-type image --page-size 5
uv run nasa.py fetch media --id art002e000192 --catalog /tmp/nasa-cat
uv run nasa.py fetch album --album Artemis_II --media-type image --catalog /tmp/nasa-cat
```

The catalog is organized as `<catalog>/<YYYY>/<MM>/<YYYY-MM-DD>/<nasa_id>/` (or `<catalog>/unknown/<nasa_id>/` when no date is available). A `catalog.txt` index at the catalog root tracks downloaded IDs for fast deduplication across runs.

## Testing

```sh
uv run python -m unittest discover tests
```

Tests live under `tests/` and use `unittest` + `unittest.mock.patch` (stdlib only). Network calls are mocked — the suite never hits the live NASA API.

## Other utilities

`inventory.py` scans a catalog directory and prints all NASA IDs found:

```sh
python inventory.py <catalog>
```

## Reference

- [NASA Image and Video Library](https://images.nasa.gov/)
  - [Usage Guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/)
  - [API Documentation](https://images.nasa.gov/docs/images.nasa.gov_api_docs.pdf) (PDF)
- [Python](https://www.python.org/)
- [UV](https://docs.astral.sh/uv/)
