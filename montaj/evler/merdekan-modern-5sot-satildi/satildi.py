"""SATILDI card: one still image (9:16 and 4:5) from the hook photo of a sold house."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "video"))
import render
from render import font, GOLD, GREEN, GREEN_DARK, CREAM, WHITE

D = Path(__file__).resolve().parent
render.PHOTOS = D / "photos"
render.LISTING = {"slug": "x", "comment_cta": True, "price": None, "phone": "", "details": ["", "", ""], "share": "",
                  "label_style": "chip", "hook": {"style": "classic", "title": [], "sub": "", "pill": ""},
                  "shots": [["hook_yard", 3.0, "in_slow", None, None]]}

for W, H, tag in [(1080, 1920, "9x16"), (1080, 1350, "4x5")]:
    r = render.Renderer(W, H, tag)
    fs, u, mx = r.fs, r.u, int(70 * W / 1080)
    im = r.kb("hook_yard", "in_slow", 0.0).convert("RGBA")
    # darken lower part for text
    g = np.zeros((H, W, 4), np.uint8)
    g0 = int(H * 0.40)
    g[g0:, :, 3] = (np.clip(np.linspace(0, 1.5, H - g0), 0, 1) ** 0.9 * 225)[:, None].astype(np.uint8)
    n = int(H * 0.22)
    g[:n, :, 3] = np.maximum(g[:n, :, 3], (np.linspace(1, 0, n) * 120)[:, None].astype(np.uint8))
    im.alpha_composite(Image.fromarray(g, "RGBA"))
    im.alpha_composite(r.watermark, r.watermark_pos)

    # rotated gold stamp "SATILDI"
    sw, sh = int(720 * fs), int(230 * fs)
    st = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    ds = ImageDraw.Draw(st)
    lw = max(4, int(9 * fs))
    ds.rounded_rectangle([lw, lw, sw - lw, sh - lw], radius=int(26 * fs), outline=GOLD + (255,), width=lw, fill=GREEN_DARK + (200,))
    ds.rounded_rectangle([3 * lw, 3 * lw, sw - 3 * lw, sh - 3 * lw], radius=int(18 * fs), outline=GOLD + (200,), width=max(2, lw // 3))
    ds.text((sw / 2, sh / 2 + 6 * fs), "SATILDI", font=font("Playfair700.ttf", 150 * fs), fill=GOLD, anchor="mm")
    st = st.rotate(8, expand=True, resample=Image.BICUBIC)
    sy = int(H * (0.24 if r.tall else 0.20))
    shadow = Image.new("RGBA", st.size, (0, 0, 0, 0))
    shadow.putalpha(st.split()[3].filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v * 0.55)))
    im.alpha_composite(shadow, (W // 2 - st.width // 2 + 8, sy + 14))
    im.alpha_composite(st, (W // 2 - st.width // 2, sy))

    d = ImageDraw.Draw(im)
    y = int(H * (0.55 if r.tall else 0.50))
    parts = []
    fb = font("Playfair700.ttf", 104 * fs)
    for i, line in enumerate(["Modern villa", "yeni sahibinə çatdı"]):
        f_ = fb if i == 0 else font("Playfair700.ttf", 70 * fs)
        parts.append((line, f_, CREAM if i == 0 else GOLD, W / 2 - d.textlength(line, font=f_) / 2, y, 0))
        y += int(120 * fs) if i == 0 else int(95 * fs)
    fsub = font("Montserrat600.ttf", 42 * fs)
    sub = "Mərdəkan  •  5 sot  •  5 otaq"
    parts.append((sub, fsub, CREAM, W / 2 - d.textlength(sub, font=fsub) / 2, y, 0))
    y += int(110 * fs)
    fm = font("Montserrat700.ttf", 46 * fs)
    for line in ["Növbəti xoşbəxt sahib", "siz ola bilərsiniz!"]:
        parts.append((line, fm, WHITE, W / 2 - d.textlength(line, font=fm) / 2, y, 0))
        y += int(64 * fs)
    im.alpha_composite(r.text_layer(parts))

    # gold pill CTA
    t = "Arzunuzdakı evi şərhdə yazın  ↓"
    fp = font("Montserrat700.ttf", 42 * fs)
    tw = d.textlength(t, font=fp)
    ph = int(100 * fs)
    yb = H - int((210 if r.tall else 150) * u) - ph
    dd = ImageDraw.Draw(im)
    dd.rounded_rectangle([W / 2 - tw / 2 - 44 * fs, yb, W / 2 + tw / 2 + 44 * fs, yb + ph], radius=ph // 2, fill=GOLD + (255,))
    dd.text((W / 2, yb + ph / 2), t, font=fp, fill=GREEN, anchor="mm")
    im.convert("RGB").save(D / "out" / f"satildi-{tag}.jpg", quality=94)
    print("saved", tag)
