import os
import re
from config import get_settings

settings = get_settings()

BASE_BOARD_DIR = os.path.join(settings.data_dir, "boards")

def resolve_board_image_path(board: str, climb: dict) -> str:
    """
    Return the filesystem path for the base board image corresponding to a climb.
    Works for Decoy, Kilter, and Tension boards.
    """
    board = board.lower()
    images_dir = os.path.join(
        BASE_BOARD_DIR,
        board,
        "images",
        "product_sizes_layouts_sets"
    )

    if not os.path.isdir(images_dir):
        raise FileNotFoundError(f"Board images directory not found: {images_dir}")

    layout_id = climb.get("layout_id")
    if layout_id is None:
        raise ValueError("Climb has no layout_id")

    # 1️⃣ Find all candidate images containing layout_id
    candidates = []
    for fname in os.listdir(images_dir):
        if not fname.lower().endswith((".png", ".jpg", ".jpeg")):
            continue
        # match exact numeric layout_id or variant (e.g., 33-2.png)
        if re.search(rf"\b{layout_id}\b", fname):
            candidates.append(fname)

    # 2️⃣ Fallback: pick first numeric file if no candidates
    if not candidates:
        numeric_files = [
            f for f in os.listdir(images_dir)
            if re.match(r"^\d+(-\d+)?\.png$", f)
        ]
        if numeric_files:
            numeric_files.sort()
            return os.path.join(images_dir, numeric_files[0])
        # fallback to first file if nothing else
        all_files = [f for f in os.listdir(images_dir) if f.lower().endswith(".png")]
        if all_files:
            all_files.sort()
            return os.path.join(images_dir, all_files[0])
        raise FileNotFoundError(
            f"No board image found for board={board}, layout_id={layout_id}"
        )

    # 3️⃣ Deterministic: pick first sorted candidate
    candidates.sort()
    return os.path.join(images_dir, candidates[0])
