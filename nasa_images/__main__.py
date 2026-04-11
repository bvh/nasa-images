import argparse
import json
import sys
from pathlib import Path
from typing import Any

from nasa_images.api import Asset, Metadata, Album, Captions, Search
from nasa_images.fetch import fetch_album_by_name, fetch_media_by_id


def main() -> None:
    args = _parse_args()
    if args.operation.lower() == "call":
        if args.operand.lower() == "asset":
            if args.id:
                manifest = call_asset(args.id)
                if manifest:
                    print(json.dumps(manifest, indent=4))
                else:
                    print(f"ERROR: no asset found for nasa_id={args.id}")
            else:
                print("ERROR: no nasa_id provided", file=sys.stderr)
        elif args.operand.lower() == "metadata":
            if args.id:
                metadata = call_metadata(args.id)
                if metadata:
                    print(json.dumps(metadata, indent=4))
                else:
                    print(f"ERROR: no metadata found for nasa_id={args.id}")
            else:
                print("ERROR: no nasa_id provided", file=sys.stderr)
        elif args.operand.lower() == "album":
            if args.album:
                album = call_album(args.album, args.page)
                if album:
                    print(json.dumps(album, indent=4))
                else:
                    print(f"ERROR: no album found for album_name={args.album}")
            else:
                print("ERROR: no album_name provided", file=sys.stderr)
        elif args.operand.lower() == "captions":
            if args.id:
                captions = call_captions(args.id)
                if captions:
                    print(json.dumps(captions, indent=4))
                else:
                    print(f"ERROR: no captions found for nasa_id={args.id}")
            else:
                print("ERROR: no nasa_id provided", file=sys.stderr)
        elif args.operand.lower() == "search":
            results = call_search(
                q=args.q,
                center=args.center,
                description=args.description,
                description_508=args.description_508,
                keywords=args.keywords,
                location=args.location,
                media_type=args.media_type,
                nasa_id=args.id,
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
        else:
            print(f"ERROR: unknown endpoint {args.operand}", file=sys.stderr)
    elif args.operation.lower() == "fetch":
        if args.operand.lower() == "media":
            if args.id:
                fetch_media_by_id(args.id, Path(args.catalog or "."))
            else:
                print("ERROR: --id is required for fetch media", file=sys.stderr)
        elif args.operand.lower() == "album":
            if args.album:
                fetch_album_by_name(
                    args.album,
                    Path(args.catalog or "."),
                    media_type=args.media_type,
                )
            else:
                print("ERROR: --album is required for fetch album", file=sys.stderr)
        else:
            print(f"ERROR: unknown fetch target {args.operand}", file=sys.stderr)
    else:
        print(f"ERROR: unknown operation {args.operation}", file=sys.stderr)


def call_asset(nasa_id: str) -> dict[str, Any] | None:
    manifest = Asset(nasa_id)
    if manifest:
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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="simple script for working with the NASA images API"
    )
    parser.add_argument("operation", help="the operation to execute")
    parser.add_argument("operand", help="the target of the operation")

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("-i", "--id", help="NASA ID of the media asset")
    group.add_argument("-a", "--album", help="name of the media album")
    parser.add_argument("-p", "--page", type=int, help="page number of results")
    parser.add_argument("--q", help="free text search terms")
    parser.add_argument("--center", help="NASA center which published the media")
    parser.add_argument("--description", help='terms to search for in "Description" fields')
    parser.add_argument("--description-508", dest="description_508", help='terms to search for in "508 Description" fields')
    parser.add_argument("--keywords", help='terms to search for in "Keywords" fields (comma-separated)')
    parser.add_argument("--location", help='terms to search for in "Location" fields')
    parser.add_argument("--media-type", dest="media_type", help="media types to restrict search to (image, video, audio)")
    parser.add_argument("--page-size", dest="page_size", type=int, help="number of results per page (default: 100)")
    parser.add_argument("--photographer", help="primary photographer's name")
    parser.add_argument("--secondary-creator", dest="secondary_creator", help="secondary photographer/videographer's name")
    parser.add_argument("--title", help='terms to search for in "Title" fields')
    parser.add_argument("--year-start", dest="year_start", help="start year for results (YYYY)")
    parser.add_argument("--year-end", dest="year_end", help="end year for results (YYYY)")
    parser.add_argument("--catalog", help="catalog root directory for fetch (default: current directory)")

    return parser.parse_args()


if __name__ == "__main__":
    main()
