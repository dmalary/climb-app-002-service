from typing import List, Dict

def parse_frames(frames_str: str, climb: dict) -> List[Dict]:
    """
    Converts a frames string into a list of holds with coordinates and type.

    Example frames string:
    "p3r4p29r2p59r1p65r2p75r3p89r2p157r4p158r4"

    Returns:
        [
            {"x": 100, "y": 200, "type": "hand"},
            {"x": 50, "y": 120, "type": "foot"},
            {"x": 180, "y": 300, "type": "finish"},
        ]
    """
    holds = []

    if not frames_str:
        return holds

    import re

    # Match all "p<number>r<number>" patterns
    pattern = re.compile(r"p(\d+)r(\d+)")
    matches = pattern.findall(frames_str)

    for i, (px, ry) in enumerate(matches):
        x = int(px)
        y = int(ry)

        # Determine hold type
        # Simple rules:
        # - first hold = start (green)
        # - last hold = finish (red)
        # - even-index = hand (blue)
        # - odd-index = foot (purple)
        if i == 0:
            type_ = "start"
        elif i == len(matches) - 1:
            type_ = "finish"
        elif i % 2 == 0:
            type_ = "hand"
        else:
            type_ = "foot"

        holds.append({"x": x, "y": y, "type": type_})

    return holds
