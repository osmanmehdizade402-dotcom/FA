"""Ev Pasportu sistem səhifəsini qurur: python3 pasport/build_sistem.py -> pasport/out/sistem.html"""
from pathlib import Path

from build import b64, LOGO, ROOT

EV = ROOT / "montaj/evler"


def main():
    html = (Path(__file__).parent / "sistem-template.html").read_text()
    subs = {
        "logo": b64(LOGO, (360, 200), "PNG"),
        "p_hero": b64(EV / "merdekan-4sot-160m/photos/facade.jpg", (760, 760)),
        "e1": b64(EV / "aciq-qapi-senbe/photos/e1_pool.jpg", (200, 200)),
        "e2": b64(EV / "aciq-qapi-senbe/photos/e2_pool_palms.jpg", (200, 200)),
        "e3": b64(EV / "aciq-qapi-senbe/photos/e3_facade.jpg", (200, 200)),
    }
    for k, v in subs.items():
        html = html.replace("{{%s}}" % k, v)
    out = Path(__file__).parent / "out/sistem.html"
    out.write_text(html)
    print(out, len(html) // 1024, "KB")


if __name__ == "__main__":
    main()
