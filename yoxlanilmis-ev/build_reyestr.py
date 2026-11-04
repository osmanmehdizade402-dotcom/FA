"""Reyestr səhifəsini qurur: python3 yoxlanilmis-ev/build_reyestr.py -> yoxlanilmis-ev/out/reyestr.html

VÖEN və əmtəə nişanı qeydiyyat nömrəsi məlum olanda aşağıdakı INFO-nu doldurun.
"""
import base64
import io
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
INFO = {"voen": "[VÖEN əlavə olunacaq]", "tm": "[müraciət nömrəsi əlavə olunacaq]"}


def main():
    im = Image.open(HERE.parent / "logo/xezer-sahil-emlak-horizontal-transparent.png")
    im.thumbnail((360, 200))
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    html = (HERE / "reyestr.html").read_text().replace("{{logo}}", base64.b64encode(buf.getvalue()).decode())
    for k, v in INFO.items():
        html = html.replace("{{%s}}" % k, v)
    out = HERE / "out/reyestr.html"
    out.write_text(html)
    print(out)


if __name__ == "__main__":
    main()
