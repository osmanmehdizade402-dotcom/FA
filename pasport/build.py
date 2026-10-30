"""Ev Pasportu prototipini qurur: şəkilləri kiçildib template.html-ə yerləşdirir.

python3 pasport/build.py [pasport_url]   ->  pasport/out/merdekan-villa.html
"""
import base64
import io
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "video/listings/merdekan-villa/photos"
LOGO = ROOT / "logo/xezer-sahil-emlak-horizontal-transparent.png"


def b64(path, size, fmt="JPEG"):
    im = Image.open(path)
    im = im.convert("RGB") if fmt == "JPEG" else im
    im.thumbnail(size)
    buf = io.BytesIO()
    im.save(buf, fmt, **({"quality": 72} if fmt == "JPEG" else {"optimize": True}))
    return base64.b64encode(buf.getvalue()).decode()


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://claude.ai"
    html = (Path(__file__).parent / "template.html").read_text()
    subs = {"facade_pool": b64(PHOTOS / "facade_pool.jpg", (1000, 1000)), "logo": b64(LOGO, (360, 200), "PNG"), "url": url}
    for n in ("living", "kitchen", "bed1", "porch_pool"):
        subs[n] = b64(PHOTOS / f"{n}.jpg", (480, 480))
    for k, v in subs.items():
        html = html.replace("{{%s}}" % k, v)
    out = Path(__file__).parent / "out/merdekan-villa.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html)
    print(out, len(html) // 1024, "KB")


if __name__ == "__main__":
    main()
