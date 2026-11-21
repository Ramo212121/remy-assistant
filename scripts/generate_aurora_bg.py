"""Generate assets/aurora_bg.png: a deep navy base with soft aurora glows and a faint grid.

Run: python scripts/generate_aurora_bg.py
"""
import struct
import zlib
from pathlib import Path

import numpy as np

WIDTH, HEIGHT = 880, 1800
GRID_SPACING = 48
OUTPUT = Path(__file__).resolve().parent.parent / "assets" / "aurora_bg.png"
rng = np.random.default_rng(7)

y, x = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)

# Üstten alta koyu lacivertten neredeyse siyaha
top, bottom = np.array([10, 16, 34], np.float32), np.array([4, 6, 14], np.float32)
image = top + (bottom - top) * (y / HEIGHT)[..., None]


def glow(cx, cy, rx, ry, color, strength):
    """A soft elliptical light, the building block of the aurora."""
    falloff = np.exp(-(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2))
    return falloff[..., None] * np.array(color, np.float32) * strength


# Kuzey ışığı: üstte camgöbeği ve mor, ortada turkuaz şerit, altta derin mor
image += glow(120, 60, 520, 360, (34, 211, 238), 0.40)
image += glow(800, 220, 420, 460, (139, 92, 246), 0.38)
image += glow(440, 760, 760, 170, (20, 184, 166), 0.18)
image += glow(60, 1350, 420, 520, (99, 102, 241), 0.26)
image += glow(840, 1650, 520, 420, (168, 85, 247), 0.30)

# Hafif dalgalı ışık perdesi, aurora hissi versin
curtain = np.exp(-((y - (330 + 70 * np.sin(x / 140.0))) / 120.0) ** 2)
image += curtain[..., None] * np.array([45, 200, 220], np.float32) * 0.12

# Silik ızgara, sadece ışığın olduğu yerde belirgin
light = image.mean(axis=2, keepdims=True) / 80.0
grid = ((x % GRID_SPACING < 1.2) | (y % GRID_SPACING < 1.2)).astype(np.float32)[..., None]
image += grid * np.minimum(light, 1.0) * np.array([40, 120, 150], np.float32) * 0.10

# Banding olmasın diye çok hafif gren
image += rng.normal(0, 1.2, image.shape).astype(np.float32)
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
