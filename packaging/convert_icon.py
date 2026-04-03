"""Convert SVG icon to ICO format for Windows executable and installer."""

import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

try:
    import cairosvg
except ImportError:
    print("cairosvg not installed, trying Pillow SVG support...")
    cairosvg = None


def svg_to_ico(svg_path: str, ico_path: str) -> None:
    """Convert an SVG file to a multi-resolution ICO file.

    Generates icon at standard Windows sizes: 16, 24, 32, 48, 64, 128, 256px.
    """
    svg_path = Path(svg_path)
    ico_path = Path(ico_path)

    if not svg_path.exists():
        print(f"Error: SVG file not found: {svg_path}")
        sys.exit(1)

    # Render SVG to PNG at the largest size
    sizes = [16, 24, 32, 48, 64, 128, 256]

    if cairosvg is None:
        print("Error: cairosvg is required for SVG-to-ICO conversion")
        sys.exit(1)

    images = []
    for size in sizes:
        png_data = cairosvg.svg2png(
            url=str(svg_path),
            output_width=size,
            output_height=size,
        )
        img = Image.open(BytesIO(png_data))
        img = img.convert("RGBA")
        images.append(img)

    # Save as ICO with all sizes
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        str(ico_path),
        format="ICO",
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:],
    )
    print(f"Created {ico_path} with sizes: {', '.join(f'{s}x{s}' for s in sizes)}")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "client/icons/app_icon.svg"
    dst = sys.argv[2] if len(sys.argv) > 2 else "client/icons/app_icon.ico"
    svg_to_ico(src, dst)
