"""Visual regression for the woven single-file player.

Screenshots the woven file in chromium (playwright, already a test dep),
decodes PNGs with the stdlib only (zlib + scanline unfilter - zero new
dependencies, honoring the keep-deps-short law), and compares against a
committed baseline. Fails when more than MAX_RATIO of pixels drift, so
UI regressions surface in CI while intentional redesigns update the
baseline deliberately:

    VISUAL_UPDATE=1 uv run python scripts/visual_regress.py <woven.html> <baseline.png>

usage: uv run python scripts/visual_regress.py <woven.html> <baseline.png>
"""

import os
import struct
import sys
import zlib
import pathlib

from playwright.sync_api import sync_playwright

TOL = 8            # per-channel difference that counts as a changed pixel
MAX_RATIO = 0.005  # 0.5% of pixels may drift before the gate fails


def _decode_png(data: bytes):
    """Return (w, h, channels, pixel bytes) for 8-bit PNGs."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos = 8
    idat = b""
    w = h = depth = ctype = None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        if typ == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", chunk[:10])
        elif typ == b"IDAT":
            idat += chunk
        pos += 12 + length
    assert depth == 8, f"unsupported bit depth {depth}"
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(idat)
    stride = w * channels
    out = bytearray(h * stride)
    prev = bytearray(stride)
    pos = 0
    for y in range(h):
        f = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        if f == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return w, h, channels, bytes(out)


def diff_ratio(a, b) -> float:
    wa, ha, ca, pa = a
    wb, hb, cb, pb = b
    if (wa, ha) != (wb, hb):
        return 1.0
    changed = 0
    total = wa * ha
    for i in range(0, total * ca, ca):
        if (abs(pa[i] - pb[i]) > TOL or abs(pa[i + 1] - pb[i + 1]) > TOL
                or abs(pa[i + 2] - pb[i + 2]) > TOL):
            changed += 1
    return changed / total


def screenshot(page_path: str, out_png: pathlib.Path) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(pathlib.Path(page_path).resolve().as_uri())
        page.click("#ts-enter")
        page.wait_for_timeout(1400)  # title fade + first paint settle
        if page.is_visible("#config"):
            page.click("#cfg-save")
            page.wait_for_timeout(600)
        page.screenshot(path=str(out_png))
        browser.close()


def main(argv: list[str]) -> int:
    woven, baseline = argv[1], pathlib.Path(argv[2])
    tmp = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "visual-regress.png"
    screenshot(woven, tmp)
    if os.environ.get("VISUAL_UPDATE") == "1" or not baseline.exists():
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_bytes(tmp.read_bytes())
        print(f"baseline written: {baseline}")
        return 0
    ratio = diff_ratio(
        _decode_png(tmp.read_bytes()),
        _decode_png(baseline.read_bytes()),
    )
    print(f"pixel drift: {ratio:.4%} (gate fails above {MAX_RATIO:.2%})")
    if ratio > MAX_RATIO:
        print("VISUAL GATE FAILED: update the baseline deliberately "
              "(VISUAL_UPDATE=1) if this drift is intended.")
        return 1
    print("visual gate: within tolerance")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
