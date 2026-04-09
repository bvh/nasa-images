#!/usr/bin/env python3
import argparse
from pathlib import Path

from nasa_images.image import Image


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp"}


def main() -> None:
    args = _parse_args()
    images = []
    if args.operation == "fetch":
        if args.id:
            image = fetch_image_by_id(args.id)
            if image.found:
                images.append(image)
        elif args.image:
            image = fetch_single_image(args.image)
            if image.found:
                images.append(image)
        elif args.list:
            images.extend(fetch_images_from_file(args.list))
        elif args.dir:
            images.extend(fetch_images_from_dir(args.dir))
        else:
            print("No operand given.")
        for image in images:
            image.download_image()
            image.write_metadata()

    else:
        print(f"Unknown operation: {args.operation}")


def fetch_images_from_file(path: str) -> list[Image]:
    images = []
    with open(path) as f:
        for line in f:
            nasa_id = line.strip()
            if nasa_id:
                image = fetch_image_by_id(nasa_id)
                if image.found:
                    images.append(image)
    return images


def fetch_images_from_dir(path: str) -> list[Image]:
    images = []
    for entry in Path(path).iterdir():
        if entry.is_file() and entry.suffix.lower() in IMAGE_SUFFIXES:
            image = fetch_single_image(str(entry))
            if image.found:
                images.append(image)
    return images


def fetch_single_image(path: str) -> int:
    return fetch_image_by_id(get_id_from_filename(path))


def fetch_image_by_id(nasa_id: str) -> Image:
    image = Image(nasa_id)
    print(image.original_url)
    return image


def get_id_from_filename(path: str) -> str:
    name = Path(path).name
    return name.split("~")[0]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="simple script for working with the NASA images API"
    )
    parser.add_argument("operation", help="the operation to execute")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--id", help="the image ID to look up")
    group.add_argument(
        "--list", help="a file containing a list of image IDs to look up"
    )
    group.add_argument("--dir", help="path to a directory of images to look up")
    group.add_argument("--image", help="path to a single image to look up")

    return parser.parse_args()


if __name__ == "__main__":
    main()
