"""Convert SVG icon to ICO format for Windows executable and installer.

Uses ImageMagick (magick CLI), which is pre-installed on GitHub Actions windows-latest.
For local use, install ImageMagick: https://imagemagick.org/script/download.php
"""

import subprocess
import sys
from pathlib import Path


def svg_to_ico(svg_path: str, ico_path: str) -> None:
    """Convert an SVG file to a multi-resolution ICO file.

    Generates icon at standard Windows sizes: 16, 24, 32, 48, 64, 128, 256px.
    """
    svg_path = Path(svg_path)
    ico_path = Path(ico_path)

    if not svg_path.exists():
        print(f"Error: SVG file not found: {svg_path}")
        sys.exit(1)

    ico_path.parent.mkdir(parents=True, exist_ok=True)

    # ImageMagick can directly produce a multi-resolution ICO from an SVG.
    # -background none preserves transparency.
    # Each -resize + -write produces one size layer, then combined into ICO.
    sizes = [16, 24, 32, 48, 64, 128, 256]
    args = ["magick", str(svg_path), "-background", "none"]
    for size in sizes:
        args += ["(", "-clone", "0", "-resize", f"{size}x{size}", ")"]
    args += ["-delete", "0", str(ico_path)]

    try:
        subprocess.run(args, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        print("Error: ImageMagick (magick) not found. Install from https://imagemagick.org")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error: magick failed: {e.stderr}")
        sys.exit(1)

    print(f"Created {ico_path} with sizes: {', '.join(f'{s}x{s}' for s in sizes)}")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "client/icons/app_icon.svg"
    dst = sys.argv[2] if len(sys.argv) > 2 else "client/icons/app_icon.ico"
    svg_to_ico(src, dst)
