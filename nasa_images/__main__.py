import argparse
import json
import sys
from pathlib import Path
from typing import Any

from nasa_images.api import Asset, Metadata, Album, Captions, Search
from nasa_images.fetch import fetch_album_by_name, fetch_media_by_id, fetch_search


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    args.func(args)


# --- call handlers ---

def _cmd_call_asset(args: argparse.Namespace) -> None:
    result = call_asset(args.id)
    if result:
        print(json.dumps(result, indent=4))
    else:
        print(f"ERROR: no asset found for nasa_id={args.id}", file=sys.stderr)


def _cmd_call_metadata(args: argparse.Namespace) -> None:
    result = call_metadata(args.id)
    if result:
        print(json.dumps(result, indent=4))
    else:
        print(f"ERROR: no metadata found for nasa_id={args.id}", file=sys.stderr)


def _cmd_call_album(args: argparse.Namespace) -> None:
    result = call_album(args.album, args.page)
    if result:
        print(json.dumps(result, indent=4))
    else:
        print(f"ERROR: no album found for album_name={args.album}", file=sys.stderr)


def _cmd_call_captions(args: argparse.Namespace) -> None:
    result = call_captions(args.id)
    if result:
        print(json.dumps(result, indent=4))
    else:
        print(f"ERROR: no captions found for nasa_id={args.id}", file=sys.stderr)


def _cmd_call_search(args: argparse.Namespace) -> None:
    results = call_search(
        q=args.q,
        center=args.center,
        description=args.description,
        description_508=args.description_508,
        keywords=args.keywords,
        location=args.location,
        media_type=args.media_type,
        nasa_id=args.nasa_id,
        page=args.page,
        page_size=args.page_size,
        photographer=args.photographer,
        secondary_creator=args.secondary_creator,
        title=args.title,
        year_start=args.year_start,
        year_end=args.year_end,
    )
    if results:
        print(json.dumps(results, indent=4))
    else:
        print("ERROR: search returned no results", file=sys.stderr)


# --- fetch handlers ---

def _cmd_fetch_media(args: argparse.Namespace) -> None:
    fetch_media_by_id(args.id, Path(args.catalog))


def _cmd_fetch_album(args: argparse.Namespace) -> None:
    fetch_album_by_name(args.album, Path(args.catalog), media_type=args.media_type)


def _cmd_fetch_search(args: argparse.Namespace) -> None:
    fetch_search(
        Path(args.catalog),
        q=args.q,
        center=args.center,
        description=args.description,
        description_508=args.description_508,
        keywords=args.keywords,
        location=args.location,
        media_type=args.media_type,
        nasa_id=args.nasa_id,
        page_size=args.page_size,
        photographer=args.photographer,
        secondary_creator=args.secondary_creator,
        title=args.title,
        year_start=args.year_start,
        year_end=args.year_end,
    )


# --- API helpers ---

def call_asset(nasa_id: str) -> dict[str, Any] | None:
    manifest = Asset(nasa_id)
    if manifest.okay:
        return manifest.data
    print(f"ERROR: asset {nasa_id} not found", file=sys.stderr)
    return None


def call_metadata(nasa_id: str) -> dict[str, Any] | None:
    metadata = Metadata(nasa_id)
    if metadata.okay:
        return metadata.data
    print(f"ERROR: metadata for {nasa_id} not found", file=sys.stderr)
    return None


def call_album(album_name: str, page: int | None = None) -> dict[str, Any] | None:
    album = Album(album_name, page)
    if album.okay:
        return album.data
    print(f"ERROR: album {album_name} not found", file=sys.stderr)
    return None


def call_captions(nasa_id: str) -> dict[str, Any] | None:
    captions = Captions(nasa_id)
    if captions.okay:
        return captions.data
    print(f"ERROR: captions for {nasa_id} not found", file=sys.stderr)
    return None


def call_search(**kwargs) -> dict[str, Any] | None:
    results = Search(**kwargs)
    if results.okay:
        return results.data
    print("ERROR: search failed", file=sys.stderr)
    return None


# --- parser ---

def _add_search_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--q", help="free text search terms")
    p.add_argument("--center", help="NASA center which published the media")
    p.add_argument("--description", help='terms to search for in "Description" fields')
    p.add_argument("--description-508", dest="description_508", help='terms to search for in "508 Description" fields')
    p.add_argument("--keywords", help='terms to search for in "Keywords" fields (comma-separated)')
    p.add_argument("--location", help='terms to search for in "Location" fields')
    p.add_argument("--media-type", dest="media_type", help="media types to restrict search to (image, video, audio)")
    p.add_argument("--nasa-id", dest="nasa_id", help="NASA ID to filter search results")
    p.add_argument("--page-size", dest="page_size", type=int, help="number of results per page (default: 100)")
    p.add_argument("--photographer", help="primary photographer's name")
    p.add_argument("--secondary-creator", dest="secondary_creator", help="secondary photographer/videographer's name")
    p.add_argument("--title", help='terms to search for in "Title" fields')
    p.add_argument("--year-start", dest="year_start", help="start year for results (YYYY)")
    p.add_argument("--year-end", dest="year_end", help="end year for results (YYYY)")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="simple script for working with the NASA images API"
    )
    ops = parser.add_subparsers(dest="operation", required=True)

    # --- call ---
    call_parser = ops.add_parser("call", help="call a NASA images API endpoint")
    call_ops = call_parser.add_subparsers(dest="operand", required=True)

    p = call_ops.add_parser("asset", help="fetch asset manifest for a NASA ID")
    p.add_argument("-i", "--id", required=True, help="NASA ID of the media asset")
    p.set_defaults(func=_cmd_call_asset)

    p = call_ops.add_parser("metadata", help="fetch metadata for a NASA ID")
    p.add_argument("-i", "--id", required=True, help="NASA ID of the media asset")
    p.set_defaults(func=_cmd_call_metadata)

    p = call_ops.add_parser("album", help="fetch an album page")
    p.add_argument("-a", "--album", required=True, help="name of the media album")
    p.add_argument("-p", "--page", type=int, help="page number of results")
    p.set_defaults(func=_cmd_call_album)

    p = call_ops.add_parser("captions", help="fetch captions for a NASA ID")
    p.add_argument("-i", "--id", required=True, help="NASA ID of the media asset")
    p.set_defaults(func=_cmd_call_captions)

    p = call_ops.add_parser("search", help="search the NASA images API")
    p.add_argument("-p", "--page", type=int, help="page number of results")
    _add_search_args(p)
    p.set_defaults(func=_cmd_call_search)

    # --- fetch ---
    fetch_parser = ops.add_parser("fetch", help="download media assets to a local catalog")
    fetch_ops = fetch_parser.add_subparsers(dest="operand", required=True)

    p = fetch_ops.add_parser("media", help="download a single asset by NASA ID")
    p.add_argument("-i", "--id", required=True, help="NASA ID of the media asset")
    p.add_argument("--catalog", default=".", help="catalog root directory (default: current directory)")
    p.set_defaults(func=_cmd_fetch_media)

    p = fetch_ops.add_parser("album", help="download all assets in an album")
    p.add_argument("-a", "--album", required=True, help="name of the media album")
    p.add_argument("--media-type", dest="media_type", help="restrict to image, video, or audio")
    p.add_argument("--catalog", default=".", help="catalog root directory (default: current directory)")
    p.set_defaults(func=_cmd_fetch_album)

    p = fetch_ops.add_parser("search", help="download assets matching a search query")
    _add_search_args(p)
    p.add_argument("--catalog", default=".", help="catalog root directory (default: current directory)")
    p.set_defaults(func=_cmd_fetch_search)

    return parser


if __name__ == "__main__":
    main()
