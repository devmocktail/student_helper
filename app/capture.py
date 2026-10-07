"""Screen-grab helpers (shared by the region selector).

We grab with `mss` (physical pixels) and crop inside the already-captured
image, which keeps selection correct even under Windows display scaling.
"""

import io

import mss
from PIL import Image


def capture_primary():
    """Grab the whole primary monitor as a PIL image (physical pixels)."""
    with mss.mss() as sct:
        raw = sct.grab(sct.monitors[1])
    return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


def to_png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
