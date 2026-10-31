"""Generate assets/hud_bg.png, the app's dark grid background. Run: python scripts/generate_hud_bg.py"""
import struct
import zlib
from pathlib import Path

import numpy as np

WIDTH, HEIGHT = 880, 1720
GRID_SPACING = 56
OUTPUT = Path(__file__).resolve().parent.parent / "assets" / "hud_bg.png"

y, x = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)

image = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)
image[..., :] = np.array([3, 7, 11], dtype=np.float32)

# Üstten gelen çok hafif camgöbeği ışık
light = np.exp(-(((x - WIDTH / 2) / 620) ** 2 + ((y + 80) / 620) ** 2))
image += light[..., None] * np.array([0, 34, 42], dtype=np.float32)

# Izgara, kenarlara doğru sönüyor
fade = np.exp(-(((x - WIDTH / 2) / 700) ** 2 + ((y - HEIGHT / 3) / 1100) ** 2))
grid = ((x % GRID_SPACING < 1.5) | (y % GRID_SPACING < 1.5)).astype(np.float32)
image += (grid * fade)[..., None] * np.array([0, 26, 32], dtype=np.float32)

pixels = np.clip(image, 0, 255).astype(np.uint8)


def chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))


raw = b"".join(b"\x00" + pixels[row].tobytes() for row in range(HEIGHT))
OUTPUT.write_bytes(
    b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0))
    + chunk(b"IDAT", zlib.compress(raw, 9))
    + chunk(b"IEND", b"")
)
print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size / 1e6:.2f} MB)")
