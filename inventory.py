#!/usr/bin/env python3
"""List all nasa_ids present in a catalog directory."""

import argparse
from pathlib import Path


def inventory(catalog: Path) -> list[str]:
    # Each nasa_id is a leaf directory at depth 4 under dated paths
    # (<catalog>/<YYYY>/<MM>/<YYYY-MM-DD>/<nasa_id>/) or depth 2 under unknown
    # (<catalog>/unknown/<nasa_id>/). In both cases the nasa_id dir contains
    # files, not subdirectories, so we collect any directory whose parent is
    # not itself a nasa_id directory.
    #
    # Simpler: a nasa_id dir is any directory that contains at least one file
    # (no subdirectories). Walk the tree and collect leaf directories.
    ids = []
    for path in catalog.rglob("*"):
        if path.is_dir() and any(p.is_file() for p in path.iterdir()):
            ids.append(path.name)
    return sorted(ids)


def main() -> None:
    parser = argparse.ArgumentParser(description="List nasa_ids in a catalog.")
    parser.add_argument("catalog", type=Path, help="Path to the catalog directory")
    args = parser.parse_args()

    if not args.catalog.is_dir():
        parser.error(f"not a directory: {args.catalog}")

    for nasa_id in inventory(args.catalog):
        print(nasa_id)


if __name__ == "__main__":
    main()
