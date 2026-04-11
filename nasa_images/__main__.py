import argparse
import json
import sys
from typing import Any

from nasa_images.api import Asset, Metadata, Album, Captions


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
        else:
            print(f"ERROR: unknown endpoint {args.operand}", file=sys.stderr)
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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="simple script for working with the NASA images API"
    )
    parser.add_argument("operation", help="the operation to execute")
    parser.add_argument("operand", help="the target of the operation")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-i", "--id", help="NASA ID of the media asset")
    group.add_argument("-a", "--album", help="name of the media album")
    parser.add_argument("-p", "--page", type=int, help="page number of results")

    return parser.parse_args()


if __name__ == "__main__":
    main()
