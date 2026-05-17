import argparse
import base64
from pathlib import Path
import sys


def image_to_base64(image_path: Path) -> str:
    if not image_path.exists():
        raise FileNotFoundError(f"File not found: {image_path}")
    if not image_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {image_path}")

    return base64.b64encode(image_path.read_bytes()).decode("ascii")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert an image file to a base64 string.",
    )
    parser.add_argument(
        "image_path",
        type=Path,
        help="Path to the image file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        print(image_to_base64(args.image_path))
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
