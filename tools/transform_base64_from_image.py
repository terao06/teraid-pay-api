import argparse
import base64
from io import BytesIO
from pathlib import Path
import sys

from PIL import Image


def image_to_base64(
    image_path: Path,
    max_size: int | None = 112,
    image_format: str | None = "JPEG",
    quality: int = 85,
    raw: bool = False,
) -> str:
    if not image_path.exists():
        raise FileNotFoundError(f"File not found: {image_path}")
    if not image_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {image_path}")

    if raw:
        image_bytes = image_path.read_bytes()
    else:
        image_bytes = encode_optimized_image(
            image_path=image_path,
            max_size=max_size,
            image_format=image_format,
            quality=quality,
        )

    return base64.b64encode(image_bytes).decode("ascii")


def encode_optimized_image(
    image_path: Path,
    max_size: int | None,
    image_format: str | None,
    quality: int,
) -> bytes:
    image = Image.open(image_path).convert("RGB")
    if max_size is not None:
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    output_format = (image_format or image.format or image_path.suffix.lstrip(".") or "JPEG").upper()
    if output_format == "JPG":
        output_format = "JPEG"

    with BytesIO() as buffer:
        save_kwargs: dict[str, int | bool] = {}
        if output_format in {"JPEG", "WEBP"}:
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True
        image.save(buffer, format=output_format, **save_kwargs)
        return buffer.getvalue()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert an image file to a base64 string.",
    )
    parser.add_argument(
        "image_path",
        type=Path,
        help="Path to the image file.",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=112,
        help="Resize the image so the longest side is at most this many pixels before encoding.",
    )
    parser.add_argument(
        "--format",
        choices=("JPEG", "PNG", "WEBP"),
        default="JPEG",
        help="Re-encode the image with this format before encoding.",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=85,
        help="JPEG/WEBP quality used when --format is JPEG or WEBP.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Encode the original image bytes without resizing or re-encoding.",
    )
    parser.add_argument(
        "--length",
        action="store_true",
        help="Print only the length of the generated base64 string.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        base64_text = image_to_base64(
            args.image_path,
            max_size=args.max_size,
            image_format=args.format,
            quality=args.quality,
            raw=args.raw,
        )
        print(len(base64_text) if args.length else base64_text)
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
