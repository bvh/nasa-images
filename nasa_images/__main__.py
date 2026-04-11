import argparse
import json
import sys
from typing import Any

from nasa_images.api import Asset, Metadata


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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="simple script for working with the NASA images API"
    )
    parser.add_argument("operation", help="the operation to execute")
    parser.add_argument("operand", help="the target of the operation")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-i", "--id", help="NASA ID of the media asset")

    return parser.parse_args()


if __name__ == "__main__":
    main()
