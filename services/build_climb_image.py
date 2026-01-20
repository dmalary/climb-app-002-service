from PIL import Image, ImageDraw
from services.render_helpers import parse_frames
import os

def build_climb_image(
    base_board_path: str,   # path to boardlib layout image
    climb: dict,            # includes frames, edges, angle, hsm
    output_path: str
):
    """
    Render a single climb image with holds overlayed on the base board.
    Saves the result to `output_path`.
    """

    if not os.path.exists(base_board_path):
        raise FileNotFoundError(f"Base board image not found at {base_board_path}")

    # 1️⃣ Open base board image
    img = Image.open(base_board_path).convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")

    # 2️⃣ Map frames -> hold coordinates
    holds = parse_frames(climb.get("frames", ""), climb)

    # 3️⃣ Draw holds
    hsm = max(1, climb.get("hsm", 1))  # fallback to 1
    for h in holds:
        x, y, type_ = h["x"], h["y"], h["type"]
        color = {
            "start": (0, 255, 0, 180),    # green
            "finish": (255, 0, 0, 180),   # red
            "hand": (0, 0, 255, 180),     # blue
            "foot": (128, 0, 128, 180),   # purple
        }.get(type_, (255, 255, 0, 180))  # fallback yellow
        radius = max(6, hsm)
        draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill=color)

    # 4️⃣ Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)
