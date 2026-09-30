"""Generate the layered-window application mark without external dependencies."""
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1] / "assets"


def rounded(x, y, left, top, right, bottom, radius):
    dx = max(left + radius - x, 0, x - right + radius)
    dy = max(top + radius - y, 0, y - bottom + radius)
    return left <= x <= right and top <= y <= bottom and dx * dx + dy * dy <= radius * radius


def pixel(x, y):
    if not rounded(x, y, 2, 2, 62, 62, 14):
        return (0, 0, 0, 0)
    color = (57, 76, 85, 255)
    if rounded(x, y, 3, 3, 61, 61, 13):
        color = (19, 31, 39, 255)
    if rounded(x, y, 12, 13, 46, 42, 5):
        color = (194, 216, 221, 255)
    if rounded(x, y, 15, 16, 43, 39, 2):
        color = (37, 54, 65, 255)
    if rounded(x, y, 21, 24, 54, 51, 5):
        color = (109, 231, 193, 255)
    if rounded(x, y, 26, 30, 49, 34, 1.5):
        color = (20, 61, 53, 255)
    if rounded(x, y, 26, 39, 39, 43, 1.5):
        color = (20, 61, 53, 255)
    return color


def png(size):
    rows = bytearray()
    samples = 4
    for y in range(size):
        rows.append(0)
        for x in range(size):
            values = [pixel((x + (sx + .5) / samples) * 64 / size,
                            (y + (sy + .5) / samples) * 64 / size)
                      for sy in range(samples) for sx in range(samples)]
            alpha = sum(p[3] for p in values)
            rgb = [round(sum(p[c] * p[3] for p in values) / alpha) if alpha else 0 for c in range(3)]
            rows.extend(rgb + [round(alpha / len(values))])
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b"")


def main():
    ROOT.mkdir(exist_ok=True)
    sizes = (16, 20, 24, 32, 48, 64, 128, 256)
    frames = [png(size) for size in sizes]
    offset = 6 + 16 * len(sizes)
    directory = bytearray(struct.pack("<HHH", 0, 1, len(sizes)))
    for size, frame in zip(sizes, frames):
        directory.extend(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(frame), offset))
        offset += len(frame)
        (ROOT / f"app-{size}.png").write_bytes(frame)
    (ROOT / "DesktopTools.ico").write_bytes(directory + b"".join(frames))


if __name__ == "__main__":
    main()
