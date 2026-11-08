"""Xəzər Sahil Əmlak — listing promo video renderer (brand template).

Everything brand-related (logo, colours, fonts, font sizes, layout, CTA box,
photo brightening, motion and transitions) is fixed here. Everything about a
specific house lives in listings/<slug>/listing.json + listings/<slug>/photos/.

Renders, into listings/<slug>/out/:
  <slug>-9x16-tiktok-reels-story.mp4   1080x1920
  <slug>-4x5-instagram-post.mp4        1080x1350
  cover-9x16.jpg, cover-4x5.jpg        first frame (use as cover)

Usage:
  python3 render.py listings/<slug>            # full render
  python3 render.py listings/<slug> --preview  # key frames only, to preview.jpg
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from straighten import straighten

ROOT = Path(__file__).resolve().parent
FONTS = ROOT / "fonts"
LOGO = ROOT.parent / "logo" / "xezer-sahil-emlak-horizontal-transparent.png"
FPS = 30
TR = 0.30  # transition length, seconds
# Pacing (user rule: slow enough that every label can be read before the next cut).
# Listing durations are minimums-adjusted here, so all listings get the same pace.
HOOK_MIN = 2.0   # hook shot: exactly 2 s (user rule, 2026-11-07)
SHOT_MIN = 2.0   # old minimum (only when a listing sets "shot_sec": null)
SHOT_SEC = 1.5   # user rule (2026-11-04): every labelled shot is exactly 1.5 s
END_DUR = 4.8    # end card: price, details, phone
# CTA line above the phone number (user rule; same for every listing until the user changes it)
CTA_TEXT = "Ətraflı məlumat və baxış üçün zəng et"
COMMENT_Q = "Bu ev neçəyə satılır?"   # old prompt (kept for listings that override comment_q)
COMMENT_A = "Şərhdə qeyd et"
# user rule (2026-11-04): comment keyword CTA in hook and end card
EV_Q = "Qiymət üçün şərhə yazın:"
EV_WORD = "“EV”"
EV_DM = "DM-ə göndərirəm"
EV_PILL = "Qiymət üçün şərhə “EV” yazın  ↓"
VERIFIED_TXT = "Xəzər Sahil — Yoxlanılmış Ev"  # badge for houses that passed the 3 checks ("verified": true)
SAVE_TXT = "SAXLA, İTİRMƏ"  # test: mid-video save prompt (listing "save_cta": shot index)


def T(key, default):
    """Per-listing text override (e.g. Ukrainian/Russian versions): listing.json "text": {key: value}."""
    return (LISTING.get("text") or {}).get(key, default)
END_LOOP = 0.4  # final crossfade back into frame 0 for a seamless loop

# ---- brand ----
GREEN = (22, 62, 58)
GREEN_DARK = (15, 46, 42)  # CTA box fill
GOLD = (194, 163, 101)
GOLD_SOFT = (214, 186, 124)  # CTA line text
CREAM = (241, 239, 232)
WHITE = (255, 255, 255)

LISTING = None  # set in main
PHOTOS = None


def az_upper(t):
    """Azerbaijani-aware uppercase: i -> İ (Python's upper() gives dotless I)."""
    return t.replace("i", "İ").upper()


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), int(size))


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def brighten(im):
    """Per-photo auto exposure: lift so the bright end sits near 0.86, never darken."""
    lum = np.asarray(im.convert("L").resize((300, 400))).astype(float) / 255
    gain = min(max(0.86 / max(np.percentile(lum, 95), 1e-3), 1.0), 1.25)
    arr = np.asarray(im).astype(float) / 255 * gain
    # soft shoulder instead of hard clipping
    arr = np.where(arr > 0.9, 0.9 + (1 - np.exp(-(arr - 0.9) / 0.1)) * 0.1, arr)
    im = Image.fromarray((arr * 255).clip(0, 255).astype(np.uint8))
    im = ImageEnhance.Color(im).enhance(1.12)
    return ImageEnhance.Contrast(im).enhance(1.05)


def grade(im, vignette=True):
    """Colour look (user rule, ref: autumn-lake reel): rich saturated warm colours, glowing
    highlights, cool teal-blue shadows, gentle S-curve and soft vignette. Keeps brightness."""
    a = np.asarray(im).astype(np.float32) / 255
    hsv = np.asarray(im.convert("HSV")).astype(np.float32) / 255
    h, s = hsv[..., 0], hsv[..., 1]
    # vibrance: lift muted colours more than already-strong ones
    lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
    amt = 0.35 + 0.6 * (1 - s) ** 1.5
    a = lum[..., None] + (a - lum[..., None]) * (1 + amt[..., None])
    # warm hues (red/orange/yellow/wood/brick) get extra richness
    warm = np.clip(1 - np.minimum(np.abs(h - 0.07), np.abs(h - 1.07)) / 0.10, 0, 1) * np.clip(s * 3, 0, 1)
    a = lum[..., None] + (a - lum[..., None]) * (1 + 0.45 * warm[..., None])
    a[..., 0] += 0.04 * warm
    a[..., 2] -= 0.02 * warm
    # blue/teal hues (sky, water, pool) a touch deeper
    cool = np.clip(1 - np.abs(h - 0.56) / 0.10, 0, 1) * np.clip(s * 3, 0, 1)
    a = lum[..., None] + (a - lum[..., None]) * (1 + 0.35 * cool[..., None])
    # split toning: teal shadows, warm golden highlights
    lum = np.clip(a @ np.array([0.299, 0.587, 0.114], np.float32), 0, 1)
    sh = np.clip(1 - lum / 0.4, 0, 1)[..., None]
    hi = np.clip((lum - 0.55) / 0.45, 0, 1)[..., None]
    a += sh * np.array([-0.04, 0.01, 0.05], np.float32) + hi * np.array([0.045, 0.018, -0.03], np.float32)
    # gentle S-curve
    a = np.clip(a, 0, 1)
    a = a + 0.35 * (a - a * a) * (2 * a - 1)  # S-curve: deeper shadows, brighter highlights
    a = np.clip(0.5 + (a - 0.5) * 1.05, 0, 1)
    if not vignette:
        return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    # soft vignette
    H, W = lum.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / np.sqrt(2)
    a *= (1 - 0.22 * np.clip((r - 0.45) / 0.55, 0, 1) ** 1.6)[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def load_clip(key, dur):
    """'video:clip.mov@0.5' -> list of graded RGB frames (FPS) from <listing>/video/, dur seconds."""
    spec = key.split(":", 1)[1]
    name, _, start = spec.partition("@")
    src = PHOTOS.parent / "video" / name
    w, h = 1080, 1920
    cmd = ["ffmpeg", "-v", "error", "-ss", start or "0", "-i", str(src), "-t", f"{dur + 0.5:.2f}",
           "-vf", f"fps={FPS},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(raw) // (w * h * 3)
    frames = np.frombuffer(raw[:n * w * h * 3], np.uint8).reshape(n, h, w, 3)
    look = clip_look(Image.fromarray(frames[n // 2]))  # same look as photos, as a 64^3 LUT + vignette
    return [look(f) for f in frames]


def clip_look(ref):
    """Fast per-clip version of brighten+grade: per-pixel colour ops baked into a LUT from a
    reference frame (exposure gain and contrast mean taken from it), spatial vignette applied after."""
    lum = np.asarray(ref.convert("L").resize((300, 400))).astype(float) / 255
    gain = min(max(0.86 / max(np.percentile(lum, 95), 1e-3), 1.0), 1.25)
    def tone(arr8):
        x = arr8.astype(float) / 255 * gain
        x = np.where(x > 0.9, 0.9 + (1 - np.exp(-(x - 0.9) / 0.1)) * 0.1, x)
        x = (x * 255).clip(0, 255)
        L = x @ np.array([0.299, 0.587, 0.114])
        x = (L[..., None] + (x - L[..., None]) * 1.12).clip(0, 255)
        return x
    rmean = (tone(np.asarray(ref.resize((270, 480)))) @ np.array([0.299, 0.587, 0.114])).mean()
    q = np.arange(64) * 4 + 2
    cube = np.stack(np.meshgrid(q, q, q, indexing="ij"), -1).reshape(512, 512, 3).astype(np.uint8)
    t = tone(cube)
    t = (rmean + (t - rmean) * 1.05).clip(0, 255).astype(np.uint8)
    lut = np.asarray(grade(Image.fromarray(t), vignette=False)).reshape(64, 64, 64, 3)
    H, W = ref.height, ref.width
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / np.sqrt(2)
    vig = (1 - 0.22 * np.clip((r - 0.45) / 0.55, 0, 1) ** 1.6)[..., None]
    def look(f):
        g = lut[f[..., 0] >> 2, f[..., 1] >> 2, f[..., 2] >> 2]
        return Image.fromarray((g * vig).astype(np.uint8))
    return look


def load_photo(key, dur=0):
    if key.startswith("video:"):
        return load_clip(key, dur)
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = PHOTOS / f"{key}{ext}"
        if p.exists():
            return grade(brighten(straighten(Image.open(p).convert("RGB"))[0]))
    raise FileNotFoundError(PHOTOS / key)


class Renderer:
    def __init__(self, W, H, tag):
        self.W, self.H, self.tag = W, H, tag
        self.tall = H / W > 1.5
        self.u = H / 1920  # vertical layout unit
        self.fs = 1.0 if self.tall else 0.86  # font scale
        smin = LISTING.get("shot_sec", SHOT_SEC)  # user rule: 1.5 s per labelled shot (null -> old 2 s minimum)
        self.shots = [(s[0], (HOOK_MIN if i == 0 else (smin if smin else max(s[1], SHOT_MIN)))) + tuple(s[2:5])
                      for i, s in enumerate(LISTING["shots"])]
        self.focus = [s[5] if len(s) > 5 else None for s in LISTING["shots"]]
        self.photos = {s[0]: load_photo(s[0], s[1]) for s in self.shots}
        self.build_overlays()

    # ---------- camera ----------
    def kb(self, key, motion, p, punch=0.0, focus=None):
        im = self.photos[key]
        if isinstance(im, list):  # video clip: real camera motion, no extra Ken Burns
            im = im[min(len(im) - 1, int(p * (len(im) - 1)))]
            motion = "none"
        iw, ih = im.size
        ar = self.W / self.H
        bw, bh = (ih * ar, ih) if iw / ih > ar else (iw, iw / ar)
        e = ease(p)
        zoom, px, py = 1.04, 0.0, 0.0
        if motion == "in":
            zoom = 1.02 + 0.10 * e
        elif motion == "in_slow":
            zoom = 1.0 + 0.07 * e
        elif motion == "in_fast":
            zoom = 1.0 + 0.22 * ease_out(p)
        elif motion == "out":
            zoom = 1.14 - 0.10 * e
        elif motion == "left":
            zoom, px = 1.10, 0.5 - e
        elif motion == "right":
            zoom, px = 1.10, e - 0.5
        elif motion == "up":
            zoom, py = 1.10, 0.5 - e
        zoom *= 1 + punch
        cw, ch = bw / zoom, bh / zoom
        if focus:  # [fx, fy, extra_zoom]: detail shot cut out of a larger photo
            fx, fy, fz = focus
            cw, ch = cw / fz, ch / fz
            x0 = fx * iw - cw / 2 + px * cw * 0.12
            y0 = fy * ih - ch / 2 + py * ch * 0.12
        else:
            sx, sy = (iw - cw) / 2, (ih - ch) / 2  # slack each side
            x0 = iw / 2 - cw / 2 + px * sx * 0.9
            y0 = ih / 2 - ch / 2 + py * sy * 0.9
        x0 = min(max(x0, 0), iw - cw)
        y0 = min(max(y0, 0), ih - ch)
        return im.resize((self.W, self.H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))

    # ---------- overlay assets ----------
    def text_layer(self, parts, shadow=True):
        """parts: list of (text, font, fill, x, y, tracking). Returns RGBA canvas."""
        lay = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for text, f, fill, x, y, track in parts:
            if track:
                cx = x
                for c in text:
                    d.text((cx, y), c, font=f, fill=fill)
                    cx += d.textlength(c, font=f) + track
            else:
                d.text((x, y), text, font=f, fill=fill)
        if not shadow:
            return lay
        a = lay.split()[3].filter(ImageFilter.GaussianBlur(10 * self.u))
        sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
        sh.putalpha(a.point(lambda v: int(v * 0.75)))
        sh.alpha_composite(lay)
        return sh

    def build_watermark(self, logo):
        """Badge + 'Xəzər Sahil Əmlak' + 'REAL ESTATE', as on the approved sample."""
        W = self.W
        k = W / 1080 * 1.2  # +20% after user feedback ("1 düyüm böyüt")
        badge_px = int(92 * k)
        # the rounded badge sits at x,y 144..719 in the 2688x864 transparent logo
        badge = logo.crop((144, 144, 720, 720)).resize((badge_px, badge_px), Image.LANCZOS)
        ft = font("Playfair700.ttf", 36 * k)
        fr = font("DejaVuSans-Bold.ttf", 20 * k)
        tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        w1 = tmp.textlength("Xəzər Sahil ", font=ft)
        w2 = tmp.textlength("Əmlak", font=ft)
        tx = badge_px + int(16 * k)
        lw, lh = int(tx + w1 + w2 + 10 * k), badge_px + int(10 * k)
        lay = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        lay.alpha_composite(badge, (0, 0))
        text = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        d = ImageDraw.Draw(text)
        ty = int(14 * k)
        d.text((tx, ty), "Xəzər Sahil ", font=ft, fill=WHITE)
        d.text((tx + w1, ty), "Əmlak", font=ft, fill=GOLD)
        x = tx + 2 * k
        for c in "REAL ESTATE":
            d.text((x, int(54 * k)), c, font=fr, fill=GOLD)
            x += tmp.textlength(c, font=fr) + 5.2 * k
        sh = text.split()[3].filter(ImageFilter.GaussianBlur(3 * k)).point(lambda v: int(v * 0.45))
        shadow = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        shadow.putalpha(sh)
        lay.alpha_composite(shadow, (int(1 * k), int(2 * k)))
        lay.alpha_composite(text)
        self.watermark = lay
        self.watermark_pos = (int(93 * W / 1080), int(170 * self.u) if self.tall else int(128 * self.H / 1350))

    def build_cta(self):
        """Dark green box with gold border: CTA line + phone, as on the approved sample."""
        W, H = self.W, self.H
        k = W / 1080
        x0, x1 = int(50 * k), W - int(50 * k)
        bh = int(150 * k)
        y0 = int(H * 0.75) if self.tall else int(1160 * H / 1350)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.rounded_rectangle([x0, y0, x1, y0 + bh], radius=int(30 * k),
                            fill=GREEN_DARK + (238,), outline=GOLD + (255,), width=max(2, int(3 * k)))
        f1 = font("DejaVuSans.ttf", 36 * k)
        f2 = font("DejaVuSans-Bold.ttf", 70 * k)
        rows = [(T("cta", CTA_TEXT), f1, GOLD_SOFT, y0 + bh * 0.25), (LISTING["phone"], f2, WHITE, y0 + bh * 0.64)]
        if LISTING.get("comment_cta"):  # user rule: comment prompt instead of the phone number
            if LISTING["hook"].get("cta_style") in ("pill", "answer"):
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(lay)
                fp = font("Montserrat700.ttf", 42 * k)
                if "comment_q" in (LISTING.get("text") or {}):
                    t = (T("comment_q", COMMENT_Q) + " " if LISTING["hook"]["cta_style"] == "pill" else "") + T("comment_a", COMMENT_A) + " ↓"
                else:
                    t = T("ev_pill", EV_PILL)
                tw = d.textlength(t, font=fp)
                ph = int(100 * k)
                yb = H - int(230 * self.u) - ph
                d.rounded_rectangle([W / 2 - tw / 2 - 40 * k, yb, W / 2 + tw / 2 + 40 * k, yb + ph], radius=ph // 2,
                                    fill=GOLD + (255,))
                d.text((W / 2, yb + ph / 2), t, font=fp, fill=GREEN, anchor="mm")
                self.cta, self.cta_top = lay, yb
                return
            rows = [(T("comment_q", COMMENT_Q), font("Montserrat700.ttf", 52 * k), WHITE, y0 + bh * 0.36),
                    (T("comment_a", COMMENT_A) + "  ↓", font("Montserrat600.ttf", 38 * k), GOLD, y0 + bh * 0.72)]
        for text, f, fill, cy in rows:
            bb = d.textbbox((0, 0), text, font=f)
            d.text((W / 2 - (bb[2] + bb[0]) / 2, cy - (bb[3] + bb[1]) / 2), text, font=f, fill=fill)
        self.cta = lay
        self.cta_top = y0

    def build_overlays(self):
        W, H, u, fs = self.W, self.H, self.u, self.fs
        mx = int(70 * W / 1080)

        # bottom gradient behind the hook text (light, keeps the photo bright)
        g = np.zeros((H, W, 4), np.uint8)
        g0 = int(H * 0.42)
        ramp = np.clip(np.linspace(0, 1.4, H - g0), 0, 1) ** 1.3
        g[g0:, :, 3] = (ramp * 120)[:, None].astype(np.uint8)
        self.grad_hook = Image.fromarray(g, "RGBA")

        logo = Image.open(LOGO).convert("RGBA")
        self.build_watermark(logo)
        self.build_cta()
        self.verified = self.verified_badge() if LISTING.get("verified") else None

        # hook
        hook = LISTING["hook"]
        self.hook_style = hook.get("style", "classic")
        if self.hook_style != "classic":
            self.build_hook_v2(hook, mx)
        f_big = font("Playfair700.ttf", 118 * fs)
        f_sub = font("Montserrat600.ttf", 42 * fs)
        y = int(H * 0.50)
        parts = []
        for i, line in enumerate(hook["title"]):
            parts.append((line, f_big, CREAM if i == 0 else GOLD, mx, y, 0))
            y += int(132 * fs)
        y += int(33 * fs)
        parts.append((hook["sub"], f_sub, CREAM, mx, y, 0))
        self.hook = self.text_layer(parts)
        f_pill = font("Montserrat700.ttf", 36 * fs)
        pill_txt = hook["pill"]
        tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        tw = tmp.textlength(pill_txt, font=f_pill)
        py = y + int(85 * fs)
        pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(pill)
        ph = int(70 * fs)
        d.rounded_rectangle([mx, py, mx + tw + 56 * fs, py + ph], radius=ph // 2, fill=GOLD + (255,))
        bb = f_pill.getbbox(pill_txt)
        d.text((mx + 28 * fs, py + (ph - (bb[3] - bb[1])) / 2 - bb[1]), pill_txt, font=f_pill, fill=GREEN)
        self.hook_pill = pill

        if self.hook_style != "classic":
            self.hook, self.hook_pill = self.hook_v2, None

        # shot labels
        f_lab = font("Montserrat700.ttf", 62 * fs)
        if LISTING.get("label_style") in ("plate", "block"):
            self.labels = {}
            style = LISTING["label_style"]
            for s in self.shots:
                lab = s[3]
                if not lab or lab in self.labels:
                    continue
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(lay)
                if style == "plate":  # small museum plate: cream, thin gold rule, serif title + tiny caps line
                    f1 = font("Playfair700.ttf", 50 * fs)
                    f2 = font("Montserrat700.ttf", 22 * fs)
                    sub = LISTING.get("plate_sub", "MƏRDƏKAN")
                    tw = max(d.textlength(lab, font=f1), d.textlength(sub, font=f2) + 40 * fs)
                    bw, bh = tw + 70 * fs, int(140 * fs)
                    x0, y0 = W - mx - bw, H - int(340 * u) - bh
                    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    ImageDraw.Draw(sh).rectangle([x0 + 8, y0 + 12, x0 + bw + 8, y0 + bh + 12], fill=(0, 0, 0, 120))
                    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12 * fs)))
                    d = ImageDraw.Draw(lay)
                    d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=CREAM + (250,))
                    d.text((x0 + 35 * fs, y0 + 28 * fs), lab, font=f1, fill=GREEN)
                    d.line([(x0 + 35 * fs, y0 + 96 * fs), (x0 + 85 * fs, y0 + 96 * fs)], fill=GOLD + (255,), width=max(2, int(3 * fs)))
                    d.text((x0 + 100 * fs, y0 + 96 * fs), sub, font=f2, fill=GOLD, anchor="lm")
                else:  # solid gold block, green caps, top-left under the logo
                    f_ = font("Montserrat700.ttf", 58 * fs)
                    t = az_upper(lab)
                    bb = d.textbbox((0, 0), t, font=f_)
                    bw, bh = bb[2] - bb[0] + 60 * fs, int(104 * fs)
                    x0 = mx
                    y0 = self.watermark_pos[1] + self.watermark.height + int(36 * fs)
                    d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=GOLD + (255,))
                    d.rectangle([x0, y0 + bh, x0 + bw * 0.35, y0 + bh + max(4, int(8 * fs))], fill=CREAM + (255,))
                    d.text((x0 + 30 * fs, y0 + bh / 2), t, font=f_, fill=GREEN, anchor="lm")
                self.labels[lab] = lay
            self.build_endcard(Image.open(LOGO).convert("RGBA"))
            return
        if LISTING.get("label_style") in ("corner", "outline"):
            self.labels = {}
            style = LISTING["label_style"]
            for s in self.shots:
                lab = s[3]
                if not lab or lab in self.labels:
                    continue
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(lay)
                if style == "corner":  # cream card in the bottom-right corner with a gold L-bracket
                    f_ = font("Playfair700.ttf", 56 * fs)
                    tw = d.textlength(lab, font=f_)
                    bw, bh = tw + 70 * fs, int(100 * fs)
                    x1, y1 = W - mx, H - int(330 * u)
                    d.rectangle([x1 - bw, y1 - bh, x1, y1], fill=CREAM + (245,))
                    lw = max(3, int(6 * fs))
                    d.line([(x1 + 14 * fs, y1 - bh - 14 * fs), (x1 + 14 * fs, y1 + 14 * fs), (x1 - bw * 0.45, y1 + 14 * fs)], fill=GOLD + (255,), width=lw)
                    d.text((x1 - bw / 2, y1 - bh / 2), lab, font=f_, fill=GREEN, anchor="mm")
                else:  # big hollow caps across the lower third, gold outline
                    t = az_upper(lab)
                    sz = 120 * fs
                    f_ = font("Montserrat700.ttf", sz)
                    while d.textlength(t, font=f_) > W - 2 * mx and sz > 40:
                        sz -= 6
                        f_ = font("Montserrat700.ttf", sz)
                    gg = np.zeros((H, W, 4), np.uint8)
                    g0 = int(H * 0.62)
                    gg[g0:, :, 3] = (np.clip(np.linspace(0, 1.2, H - g0), 0, 1) * 120)[:, None].astype(np.uint8)
                    lay.alpha_composite(Image.fromarray(gg, "RGBA"))
                    d = ImageDraw.Draw(lay)
                    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    ImageDraw.Draw(sh).text((W / 2, H - int(360 * u)), t, font=f_, fill=(0, 0, 0, 255), anchor="mm",
                                            stroke_width=max(4, int(10 * fs)), stroke_fill=(0, 0, 0, 255))
                    sh = sh.filter(ImageFilter.GaussianBlur(14 * fs))
                    sh.putalpha(sh.split()[3].point(lambda v: int(v * 0.75)))
                    lay.alpha_composite(sh)
                    d = ImageDraw.Draw(lay)
                    d.text((W / 2, H - int(360 * u)), t, font=f_, fill=GREEN_DARK + (110,), anchor="mm",
                           stroke_width=max(3, int(6 * fs)), stroke_fill=GOLD + (255,))
                self.labels[lab] = lay
            self.build_endcard(Image.open(LOGO).convert("RGBA"))
            return
        if LISTING.get("label_style") in ("rule", "leader"):
            self.labels = {}
            style = LISTING["label_style"]
            for s in self.shots:
                lab = s[3]
                if not lab or lab in self.labels:
                    continue
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                gg = np.zeros((H, W, 4), np.uint8)
                g0 = int(H * 0.64)
                gg[g0:, :, 3] = (np.clip(np.linspace(0, 1.2, H - g0), 0, 1) * 140)[:, None].astype(np.uint8)
                lay.alpha_composite(Image.fromarray(gg, "RGBA"))
                d = ImageDraw.Draw(lay)
                if style == "rule":
                    f_ = font("Montserrat700.ttf", 46 * fs)
                    t = az_upper(lab)
                    tr_ = 8 * fs
                    tw = sum(d.textlength(c, font=f_) + tr_ for c in t) - tr_
                    y = H - int(340 * u) - int(40 * fs)
                    lay.alpha_composite(self.text_layer([(t, f_, CREAM, W / 2 - tw / 2, y - 28 * fs, tr_)]))
                    d = ImageDraw.Draw(lay)
                    gap, ln = 34 * fs, 120 * fs
                    lw = max(2, int(3 * fs))
                    d.line([(W / 2 - tw / 2 - gap - ln, y), (W / 2 - tw / 2 - gap, y)], fill=GOLD + (255,), width=lw)
                    d.line([(W / 2 + tw / 2 + gap, y), (W / 2 + tw / 2 + gap + ln, y)], fill=GOLD + (255,), width=lw)
                    for xd in (W / 2 - tw / 2 - gap, W / 2 + tw / 2 + gap):
                        r_ = 7 * fs
                        d.polygon([(xd, y - r_), (xd + r_, y), (xd, y + r_), (xd - r_, y)], fill=GOLD + (255,))
                else:
                    f_ = font("Montserrat700.ttf", 48 * fs)
                    tw = d.textlength(lab, font=f_)
                    bh = int(84 * fs)
                    by = H - int(360 * u) - bh
                    bx = mx
                    d.rounded_rectangle([bx, by, bx + tw + 52 * fs, by + bh], radius=int(14 * fs), fill=GREEN_DARK + (235,))
                    d.rectangle([bx, by + bh - max(3, int(5 * fs)), bx + tw + 52 * fs, by + bh], fill=GOLD + (255,))
                    d.text((bx + 26 * fs, by + bh / 2), lab, font=f_, fill=CREAM, anchor="lm")
                    px, py = bx + tw + 52 * fs + 120 * fs, by - 70 * fs
                    lw = max(2, int(3 * fs))
                    d.line([(bx + tw + 52 * fs, by + bh / 2), (px - 40 * fs, by + bh / 2), (px, py)], fill=CREAM + (255,), width=lw)
                    r_ = 13 * fs
                    d.ellipse([px - r_ - 6 * fs, py - r_ - 6 * fs, px + r_ + 6 * fs, py + r_ + 6 * fs], outline=GOLD + (255,), width=lw)
                    d.ellipse([px - r_ * 0.6, py - r_ * 0.6, px + r_ * 0.6, py + r_ * 0.6], fill=GOLD + (255,))
                self.labels[lab] = lay
            self.build_endcard(Image.open(LOGO).convert("RGBA"))
            return
        if LISTING.get("label_style") in ("pinlab", "vertical"):
            self.labels = {}
            style = LISTING["label_style"]
            for s in self.shots:
                lab = s[3]
                if not lab or lab in self.labels:
                    continue
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                if style == "pinlab":  # gold map pin + caption + thin gold underline, bottom-left
                    gg = np.zeros((H, W, 4), np.uint8)
                    g0 = int(H * 0.66)
                    gg[g0:, :, 3] = (np.clip(np.linspace(0, 1.2, H - g0), 0, 1) * 130)[:, None].astype(np.uint8)
                    lay.alpha_composite(Image.fromarray(gg, "RGBA"))
                    d = ImageDraw.Draw(lay)
                    f_ = font("Montserrat700.ttf", 56 * fs)
                    y0 = H - int(340 * u) - int(80 * fs)
                    R = int(24 * fs)
                    px, py = mx + R, y0 + int(34 * fs)
                    d.ellipse([px - R, py - 2 * R, px + R, py], fill=GOLD + (255,))
                    d.polygon([(px - R * 0.72, py - R * 0.5), (px + R * 0.72, py - R * 0.5), (px, py + R * 0.95)], fill=GOLD + (255,))
                    d.ellipse([px - R * 0.4, py - R * 1.4, px + R * 0.4, py - R * 0.6], fill=GREEN + (255,))
                    tx = mx + 2 * R + int(26 * fs)
                    tw = d.textlength(lab, font=f_)
                    lay.alpha_composite(self.text_layer([(lab, f_, CREAM, tx, y0 - int(22 * fs), 0)]))
                    d = ImageDraw.Draw(lay)
                    d.rectangle([tx, y0 + int(62 * fs), tx + tw, y0 + int(62 * fs) + max(2, int(4 * fs))], fill=GOLD + (255,))
                else:  # vertical tracked caps along the left edge with a gold rule
                    f_ = font("Montserrat700.ttf", 54 * fs)
                    t = az_upper(lab)
                    tr_ = 10 * fs
                    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
                    tw = int(sum(tmp.textlength(c, font=f_) + tr_ for c in t) - tr_) + 20
                    th = int(80 * fs)
                    strip = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
                    ds = ImageDraw.Draw(strip)
                    x = 10
                    for c in t:
                        ds.text((x, th / 2), c, font=f_, fill=CREAM, anchor="lm")
                        x += ds.textlength(c, font=f_) + tr_
                    sh = Image.new("RGBA", strip.size, (0, 0, 0, 0))
                    sh.putalpha(strip.split()[3].filter(ImageFilter.GaussianBlur(8 * fs)).point(lambda v: int(v * 0.8)))
                    sh.alpha_composite(strip)
                    rot = sh.rotate(90, expand=True, resample=Image.BICUBIC)
                    yb = H - int(380 * u)
                    xl = int(40 * W / 1080)
                    lay.alpha_composite(rot, (xl, yb - rot.height))
                    d = ImageDraw.Draw(lay)
                    lx = xl + rot.width + int(12 * fs)
                    d.rectangle([lx, yb - rot.height, lx + max(3, int(5 * fs)), yb], fill=GOLD + (255,))
                self.labels[lab] = lay
            self.build_endcard(Image.open(LOGO).convert("RGBA"))
            return
        if LISTING.get("label_style") == "stub":
            # small cream ticket stub (matches the ticket hook), right-aligned, perforated left edge
            self.labels = {}
            for s in self.shots:
                lab = s[3]
                if not lab or lab in self.labels:
                    continue
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(lay)
                f_ = font("Playfair700.ttf", 58 * fs)
                tw = d.textlength(lab, font=f_)
                bh = int(104 * fs)
                bw = tw + 110 * fs
                x1 = W - mx
                x0 = x1 - bw
                y0 = H - int(340 * u) - bh
                d.rounded_rectangle([x0, y0, x1, y0 + bh], radius=int(16 * fs), fill=CREAM + (248,))
                r_ = int(14 * fs)
                d.ellipse([x0 + 40 * fs - r_, y0 - r_, x0 + 40 * fs + r_, y0 + r_], fill=(0, 0, 0, 0))
                d.ellipse([x0 + 40 * fs - r_, y0 + bh - r_, x0 + 40 * fs + r_, y0 + bh + r_], fill=(0, 0, 0, 0))
                for yy in range(int(y0 + r_ * 1.5), int(y0 + bh - r_ * 1.2), int(16 * fs)):
                    d.line([(x0 + 40 * fs, yy), (x0 + 40 * fs, yy + 7 * fs)], fill=GOLD + (255,), width=max(2, int(3 * fs)))
                d.text((x0 + 70 * fs, y0 + bh / 2), lab, font=f_, fill=GREEN, anchor="lm")
                self.labels[lab] = lay
            self.build_endcard(Image.open(LOGO).convert("RGBA"))
            return
        if LISTING.get("label_style") in ("osd", "lower"):
            self.labels = {}
            style = LISTING["label_style"]
            for s in self.shots:
                lab = s[3]
                if not lab or lab in self.labels:
                    continue
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(lay)
                if style == "osd":  # camera OSD: [ LABEL ] with corner ticks, white mono-ish caps
                    f_ = font("Montserrat700.ttf", 52 * fs)
                    t = az_upper(lab)
                    tr_ = 6 * fs
                    tw = sum(d.textlength(c, font=f_) + tr_ for c in t) - tr_
                    x0, y0 = mx, H - int(360 * u) - int(110 * fs)
                    bw, bh = tw + 80 * fs, int(110 * fs)
                    L, lw = int(28 * fs), max(3, int(5 * fs))
                    for (x, y, sx, sy) in [(x0, y0, 1, 1), (x0 + bw, y0, -1, 1), (x0, y0 + bh, 1, -1), (x0 + bw, y0 + bh, -1, -1)]:
                        d.line([(x, y), (x + sx * L, y)], fill=GOLD + (255,), width=lw)
                        d.line([(x, y), (x, y + sy * L)], fill=GOLD + (255,), width=lw)
                    parts = []
                    x = x0 + 40 * fs
                    lay.alpha_composite(self.text_layer([(t, f_, WHITE, x, y0 + bh / 2 - 30 * fs, tr_)]))
                else:  # news lower third: gold square + green bar with cream label, thin cream line under
                    f_ = font("Montserrat700.ttf", 50 * fs)
                    tw = d.textlength(lab, font=f_)
                    bh = int(96 * fs)
                    y0 = H - int(330 * u) - bh
                    sq = bh
                    d.rectangle([0, y0, sq, y0 + bh], fill=GOLD + (255,))
                    d.rectangle([sq, y0, sq + tw + 80 * fs, y0 + bh], fill=GREEN_DARK + (235,))
                    d.rectangle([0, y0 + bh, sq + tw + 80 * fs, y0 + bh + max(3, int(6 * fs))], fill=CREAM + (255,))
                    d.text((sq + 40 * fs, y0 + bh / 2), lab, font=f_, fill=CREAM, anchor="lm")
                    cx_, cy_ = sq / 2, y0 + bh / 2
                    r_ = bh * 0.18
                    d.polygon([(cx_ - r_, cy_ - r_ * 1.2), (cx_ - r_, cy_ + r_ * 1.2), (cx_ + r_ * 1.3, cy_)], fill=GREEN)
                self.labels[lab] = lay
            self.build_endcard(Image.open(LOGO).convert("RGBA"))
            return
        if LISTING.get("label_style") in ("index", "toppill"):
            # index: gold running number + caption bottom-left; toppill: cream pill centred under the logo
            self.labels = {}
            style = LISTING["label_style"]
            k = 0
            for s in self.shots:
                lab = s[3]
                if not lab or lab in self.labels:
                    continue
                k += 1
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(lay)
                if style == "index":
                    gg = np.zeros((H, W, 4), np.uint8)
                    g0 = int(H * 0.60)
                    gg[g0:, :, 3] = (np.clip(np.linspace(0, 1.2, H - g0), 0, 1) * 140)[:, None].astype(np.uint8)
                    lay.alpha_composite(Image.fromarray(gg, "RGBA"))
                    fn_ = font("Playfair700.ttf", 120 * fs)
                    fl_ = font("Montserrat700.ttf", 50 * fs)
                    y0 = H - int(330 * u) - int(150 * fs)
                    num = f"{k:02d}"
                    nw = d.textlength(num, font=fn_)
                    lay.alpha_composite(self.text_layer([(num, fn_, GOLD, mx, y0, 0),
                                                         (az_upper(lab), fl_, CREAM, mx + nw + int(30 * fs), y0 + int(52 * fs), 4 * fs)]))
                else:
                    fp_ = font("Montserrat700.ttf", 46 * fs)
                    tw = d.textlength(lab, font=fp_)
                    ph_ = int(88 * fs)
                    yb = self.watermark_pos[1] + self.watermark.height + int(40 * fs)
                    d.rounded_rectangle([W / 2 - tw / 2 - 46 * fs, yb, W / 2 + tw / 2 + 46 * fs, yb + ph_], radius=ph_ // 2,
                                        fill=CREAM + (240,))
                    d.text((W / 2, yb + ph_ / 2), lab, font=fp_, fill=GREEN, anchor="mm")
                self.labels[lab] = lay
            self.build_endcard(Image.open(LOGO).convert("RGBA"))
            return
        if LISTING.get("label_style") == "serif":
            # large serif caption bottom-left with a short gold rule above it
            self.labels = {}
            fsf = font("Playfair700.ttf", 84 * fs)
            for s in self.shots:
                lab = s[3]
                if not lab or lab in self.labels:
                    continue
                y0 = H - int(360 * u) - int(100 * fs)
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                gg = np.zeros((H, W, 4), np.uint8)
                g0 = int(H * 0.62)
                gg[g0:, :, 3] = (np.clip(np.linspace(0, 1.2, H - g0), 0, 1) * 150)[:, None].astype(np.uint8)
                lay.alpha_composite(Image.fromarray(gg, "RGBA"))
                d = ImageDraw.Draw(lay)
                d.rectangle([mx, y0 - int(24 * fs), mx + int(90 * fs), y0 - int(18 * fs)], fill=GOLD + (255,))
                lay.alpha_composite(self.text_layer([(lab, fsf, CREAM, mx, y0, 0)]))
                self.labels[lab] = lay
            self.build_endcard(Image.open(LOGO).convert("RGBA"))
            return
        if LISTING.get("label_style") in ("band", "tag"):
            self.labels = {}
            style = LISTING["label_style"]
            for s in self.shots:
                lab = s[3]
                if not lab or lab in self.labels:
                    continue
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(lay)
                if style == "band":  # full-width translucent band, tracked capitals between gold rules
                    fb = font("Montserrat700.ttf", 46 * fs)
                    txt = az_upper(lab)
                    tr_ = 9 * fs
                    tw = sum(d.textlength(c, font=fb) + tr_ for c in txt) - tr_
                    bh_ = int(120 * fs)
                    yb = H - int(330 * u) - bh_
                    d.rectangle([0, yb, W, yb + bh_], fill=GREEN_DARK + (190,))
                    d.rectangle([0, yb, W, yb + max(2, int(3 * fs))], fill=GOLD + (255,))
                    d.rectangle([0, yb + bh_ - max(2, int(3 * fs)), W, yb + bh_], fill=GOLD + (255,))
                    x = W / 2 - tw / 2
                    for c in txt:
                        d.text((x, yb + bh_ / 2), c, font=fb, fill=CREAM, anchor="lm")
                        x += d.textlength(c, font=fb) + tr_
                else:  # sharp gold tag, left aligned, green text
                    ft_ = font("Montserrat700.ttf", 48 * fs)
                    tw = d.textlength(lab, font=ft_)
                    th_ = int(92 * fs)
                    yb = int(H * (0.66 if self.tall else 0.68))
                    d.rectangle([0, yb, mx + tw + 40 * fs, yb + th_], fill=GOLD + (245,))
                    d.polygon([(mx + tw + 40 * fs, yb), (mx + tw + 40 * fs + th_ / 2, yb + th_ / 2), (mx + tw + 40 * fs, yb + th_)],
                              fill=GOLD + (245,))
                    d.text((mx, yb + th_ / 2), lab, font=ft_, fill=GREEN, anchor="lm")
                self.labels[lab] = lay
            self.build_endcard(Image.open(LOGO).convert("RGBA"))
            return
        if LISTING.get("label_style") == "chip":
            self.labels = {}
            fc = font("Montserrat700.ttf", 50 * fs)
            for s in self.shots:
                lab = s[3]
                if not lab or lab in self.labels:
                    continue
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(lay)
                tw = d.textlength(lab, font=fc)
                ch = int(96 * fs)
                yb = H - int(300 * u) - ch
                d.rounded_rectangle([W / 2 - tw / 2 - 44 * fs, yb, W / 2 + tw / 2 + 44 * fs, yb + ch], radius=ch // 2,
                                    fill=GREEN_DARK + (225,), outline=GOLD + (255,), width=max(2, int(3 * fs)))
                d.text((W / 2, yb + ch / 2), lab, font=fc, fill=CREAM, anchor="mm")
                self.labels[lab] = lay
            self.build_endcard(Image.open(LOGO).convert("RGBA"))
            return
        self.labels = {}
        ly = int(1180 * u) if self.tall else int(H * 0.70)
        for s in self.shots:
            lab = s[3]
            if not lab or lab in self.labels:
                continue
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            bb = f_lab.getbbox(lab)
            th = bb[3] - bb[1]
            d.rectangle([mx, ly, mx + int(10 * fs), ly + th + int(20 * fs)], fill=GOLD + (255,))
            t = self.text_layer([(lab, f_lab, CREAM, mx + int(30 * fs), ly + int(10 * fs) - bb[1], 0)])
            lay.alpha_composite(t)
            self.labels[lab] = lay

        self.build_endcard(logo)

    def build_hook_v2(self, hook, mx):
        """Alternative hook designs (user rule: every house looks different)."""
        W, H, fs, u = self.W, self.H, self.fs, self.u
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        g = np.zeros((H, W, 4), np.uint8)
        if self.hook_style == "pov":
            n = int(H * 0.45)
            g[:n, :, 3] = (np.linspace(1, 0, n) ** 0.9 * 230)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            parts = [("POV:", font("Montserrat700.ttf", 58 * fs), GOLD, mx, int(330 * u), 0)]
            fl = font("Playfair700.ttf", 92 * fs)
            for i, line in enumerate(hook["lines"]):
                parts.append((line, fl, WHITE, mx, int(410 * u) + int(108 * fs) * i, 0))
            lay.alpha_composite(self.text_layer(parts))
            self.watermark_pos = (W - self.watermark.width - int(60 * W / 1080), self.watermark_pos[1])
        elif self.hook_style == "guess":
            g0 = int(H * 0.52)
            ramp = np.clip(np.linspace(0, 1.5, H - g0), 0, 1)
            g[g0:, :, 3] = (ramp * 215)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            cy = int(H * (0.24 if self.tall else 0.27))
            self.guess_center = (W // 2, cy)
            self.guess_r = int(120 * fs)
            lay.alpha_composite(self.text_layer([(hook["kicker"], font("Montserrat700.ttf", 60 * fs), WHITE,
                                                  W / 2 - ImageDraw.Draw(lay).textlength(hook["kicker"], font=font("Montserrat700.ttf", 60 * fs)) / 2,
                                                  cy + self.guess_r + int(30 * fs), 0)]))
            fq = font("Playfair700.ttf", 120 * fs)
            y = int(H * (0.53 if self.tall else 0.55))
            d = ImageDraw.Draw(lay)
            parts = []
            for i, line in enumerate(hook["lines"]):
                parts.append((line, fq, CREAM if i == 0 else GOLD, W / 2 - d.textlength(line, font=fq) / 2, y, 0))
                y += int(130 * fs)
            fsub = font("Montserrat600.ttf", 42 * fs)
            parts.append((hook["sub"], fsub, CREAM, W / 2 - d.textlength(hook["sub"], font=fsub) / 2, y + int(10 * fs), 0))
            lay.alpha_composite(self.text_layer(parts))
            self.guess_nums = {}
            fn = font("Playfair700.ttf", 190 * fs)
            for n in range(1, 6):
                L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                dd = ImageDraw.Draw(L)
                x, yc, r = W // 2, cy, self.guess_r
                dd.ellipse([x - r, yc - r, x + r, yc + r], fill=GOLD + (255,))
                dd.text((x, yc + int(8 * fs)), str(n), font=fn, fill=GREEN, anchor="mm")
                self.guess_nums[n] = L
        elif self.hook_style == "stat":
            # one giant number (e.g. "3.5 SOT") + what fits into it, top-left block
            n = int(H * 0.62)
            g[:n, :, 3] = (np.linspace(1, 0, n) ** 1.1 * 215)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            y = int(H * (0.17 if self.tall else 0.20))
            fk = font("Montserrat700.ttf", 46 * fs)
            fbig = font("Playfair700.ttf", 250 * fs)
            fl = font("Playfair700.ttf", 84 * fs)
            parts = [(hook["kicker"], fk, CREAM, mx, y, 6 * fs)]
            y += int(70 * fs)
            parts.append((hook["big"], fbig, GOLD, mx - int(8 * fs), y, 0))
            y += int(380 * fs)
            for line in hook["lines"]:
                parts.append((line, fl, WHITE, mx, y, 0))
                y += int(100 * fs)
            lay.alpha_composite(self.text_layer(parts))
            d = ImageDraw.Draw(lay)
            d.rectangle([mx, y + int(20 * fs), mx + int(160 * fs), y + int(28 * fs)], fill=GOLD + (255,))
            self.watermark_pos = (W - self.watermark.width - int(60 * W / 1080), int(60 * u) if self.tall else int(40 * H / 1350))
        elif self.hook_style == "checklist":
            # frosted green card with ticked features, ticks appear one by one
            cw_ = W - 2 * mx
            items = hook["lines"]
            fh = font("Playfair700.ttf", 78 * fs)
            fi = font("Montserrat700.ttf", 52 * fs)
            rh = int(92 * fs)
            chh = int(150 * fs) + rh * len(items) + int(40 * fs)
            n = int(H * 0.25)
            g[:n, :, 3] = (np.linspace(1, 0, n) * 150)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            y0 = int(H * (0.30 if self.tall else 0.22))
            card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dc = ImageDraw.Draw(card)
            dc.rounded_rectangle([mx, y0, mx + cw_, y0 + chh], radius=int(36 * fs),
                                 fill=GREEN_DARK + (215,), outline=GOLD + (255,), width=max(2, int(3 * fs)))
            dc.text((mx + int(50 * fs), y0 + int(40 * fs)), hook["kicker"], font=fh, fill=GOLD)
            lay.alpha_composite(card)
            self.check_rows = []
            for j, it in enumerate(items):
                L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                dl = ImageDraw.Draw(L)
                yy = y0 + int(160 * fs) + rh * j
                bx, bs = mx + int(50 * fs), int(54 * fs)
                dl.rounded_rectangle([bx, yy, bx + bs, yy + bs], radius=int(10 * fs), fill=GOLD + (255,))
                dl.line([(bx + bs * 0.22, yy + bs * 0.52), (bx + bs * 0.43, yy + bs * 0.74), (bx + bs * 0.80, yy + bs * 0.28)],
                        fill=GREEN, width=max(3, int(8 * fs)), joint="curve")
                dl.text((bx + bs + int(30 * fs), yy + bs / 2), it, font=fi, fill=CREAM, anchor="lm")
                self.check_rows.append(L)
        elif self.hook_style == "cinema":
            # letterbox bars + film-subtitle line, logo inside the top bar
            bh = int(H * (0.14 if self.tall else 0.10))
            dl = ImageDraw.Draw(lay)
            dl.rectangle([0, 0, W, bh], fill=(8, 14, 13, 255))
            dl.rectangle([0, H - bh, W, H], fill=(8, 14, 13, 255))
            g0 = int(H * 0.30)
            ramp = np.clip(np.linspace(0, 2.2, H - g0), 0, 1)
            g[g0:, :, 3] = (ramp * 200)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            dl = ImageDraw.Draw(lay)
            dl.rectangle([0, 0, W, bh], fill=(8, 14, 13, 255))
            dl.rectangle([0, H - bh, W, H], fill=(8, 14, 13, 255))
            fk = font("Montserrat600.ttf", 40 * fs)
            fl = font("Playfair700.ttf", 96 * fs)
            y = int(H * (0.50 if self.tall else 0.46))
            parts = [(hook["kicker"], fk, GOLD, W / 2 - dl.textlength(hook["kicker"], font=fk) / 2 - 4 * len(hook["kicker"]) * fs / 2, y, 4 * fs)]
            y += int(80 * fs)
            for i, line in enumerate(hook["lines"]):
                parts.append((line, fl, CREAM if i == 0 else GOLD, W / 2 - dl.textlength(line, font=fl) / 2, y, 0))
                y += int(112 * fs)
            fsub = font("Montserrat600.ttf", 40 * fs)
            parts.append((hook["sub"], fsub, CREAM, W / 2 - dl.textlength(hook["sub"], font=fsub) / 2, y + int(16 * fs), 0))
            lay.alpha_composite(self.text_layer(parts))
            self.watermark_pos = (int(W / 2 - self.watermark.width / 2), int((bh - self.watermark.height) / 2))
        elif self.hook_style == "beats":
            # short punchy lines stacked in the middle, revealed one by one (rows reuse check_rows timing)
            c0, c1 = int(H * 0.28), int(H * 0.72)
            prof = np.sin(np.linspace(0, np.pi, c1 - c0)) ** 0.8
            g[c0:c1, :, 3] = (prof * 205)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            fl = font("Playfair700.ttf", 112 * fs)
            d = ImageDraw.Draw(lay)
            n = len(hook["lines"])
            step = int(150 * fs)
            y = int(H * 0.50) - step * n // 2
            self.check_rows = []
            for i, line in enumerate(hook["lines"]):
                col = GOLD if i == n - 1 else CREAM
                fz = fl
                sz = 112 * fs
                while d.textlength(line, font=fz) > W - 2 * mx and sz > 40:
                    sz -= 4
                    fz = font("Playfair700.ttf", sz)
                self.check_rows.append(self.text_layer([(line, fz, col, W / 2 - d.textlength(line, font=fz) / 2, y + step * i, 0)]))
            self.watermark_pos = (int(W / 2 - self.watermark.width / 2), self.watermark_pos[1])
        elif self.hook_style == "ribbon":
            # thin gold inset frame + diagonal corner ribbon + bottom-left title
            g0 = int(H * 0.50)
            ramp = np.clip(np.linspace(0, 1.4, H - g0), 0, 1)
            g[g0:, :, 3] = (ramp * 200)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            d = ImageDraw.Draw(lay)
            ins = int(28 * W / 1080)
            d.rectangle([ins, ins, W - ins, H - ins], outline=GOLD + (255,), width=max(2, int(4 * fs)))
            fr_ = font("Montserrat700.ttf", 44 * fs)
            rl = int(560 * fs)
            rh = int(84 * fs)
            rib = Image.new("RGBA", (rl, rh), GOLD + (255,))
            dr = ImageDraw.Draw(rib)
            dr.text((rl / 2, rh / 2), hook["kicker"], font=fr_, fill=GREEN, anchor="mm")
            rib = rib.rotate(-45, expand=True, resample=Image.BICUBIC)
            lay.alpha_composite(rib, (W - int(rib.width * 0.78), -int(rib.height * 0.22)))
            fl = font("Playfair700.ttf", 104 * fs)
            fsub = font("Montserrat600.ttf", 42 * fs)
            y = int(H * (0.53 if self.tall else 0.47))
            parts = []
            for i, line in enumerate(hook["lines"]):
                parts.append((line, fl, CREAM if i == 0 else GOLD, mx, y, 0))
                y += int(120 * fs)
            parts.append((hook["sub"], fsub, CREAM, mx, y + int(14 * fs), 0))
            lay.alpha_composite(self.text_layer(parts))
        elif self.hook_style == "split":
            # photo on top, solid brand panel below with the text
            p0 = int(H * (0.58 if self.tall else 0.47))
            d = ImageDraw.Draw(lay)
            d.rectangle([0, p0, W, H], fill=GREEN + (255,))
            d.rectangle([0, p0, W, p0 + max(3, int(8 * fs))], fill=GOLD + (255,))
            fk = font("Montserrat700.ttf", 40 * fs)
            fl = font("Playfair700.ttf", 100 * fs)
            fsub = font("Montserrat600.ttf", 40 * fs)
            y = p0 + int(60 * fs)
            parts = [(hook["kicker"], fk, GOLD, mx, y, 6 * fs)]
            y += int(70 * fs)
            for i, line in enumerate(hook["lines"]):
                parts.append((line, fl, CREAM if i == 0 else GOLD, mx, y, 0))
                y += int(115 * fs)
            parts.append((hook["sub"], fsub, CREAM, mx, y + int(10 * fs), 0))
            lay.alpha_composite(self.text_layer(parts, shadow=False))
        elif self.hook_style == "arch":
            # photo seen through an arched window cut into a green wall (echoes the house's arches)
            m = Image.new("L", (W, H), 255)
            dm = ImageDraw.Draw(m)
            ax0, ax1 = (int(W * 0.10), int(W * 0.90)) if self.tall else (int(W * 0.20), int(W * 0.80))
            r = (ax1 - ax0) // 2
            atop = int(H * (0.17 if self.tall else 0.12))
            abot = int(H * (0.60 if self.tall else 0.50))
            dm.pieslice([ax0, atop, ax1, atop + 2 * r], 180, 360, fill=0)
            dm.rectangle([ax0, atop + r, ax1, abot], fill=0)
            wall = Image.new("RGBA", (W, H), GREEN + (255,))
            wall.putalpha(m)
            lay.alpha_composite(wall)
            d = ImageDraw.Draw(lay)
            lw = max(3, int(6 * fs))
            d.arc([ax0 - lw, atop - lw, ax1 + lw, atop + 2 * r + lw], 180, 360, fill=GOLD + (255,), width=lw)
            d.line([(ax0 - lw // 2, atop + r), (ax0 - lw // 2, abot)], fill=GOLD + (255,), width=lw)
            d.line([(ax1 + lw // 2, atop + r), (ax1 + lw // 2, abot)], fill=GOLD + (255,), width=lw)
            fk = font("Montserrat700.ttf", 38 * fs)
            fl = font("Playfair700.ttf", 96 * fs)
            fsub = font("Montserrat600.ttf", 40 * fs)
            y = abot + int(50 * fs)
            tr_ = 8 * fs
            kw = sum(d.textlength(c, font=fk) + tr_ for c in hook["kicker"]) - tr_
            parts = [(hook["kicker"], fk, GOLD, W / 2 - kw / 2, y, tr_)]
            y += int(70 * fs)
            for i, line in enumerate(hook["lines"]):
                parts.append((line, fl, CREAM if i == 0 else GOLD, W / 2 - d.textlength(line, font=fl) / 2, y, 0))
                y += int(110 * fs)
            parts.append((hook["sub"], fsub, CREAM, W / 2 - d.textlength(hook["sub"], font=fsub) / 2, y + int(8 * fs), 0))
            lay.alpha_composite(self.text_layer(parts, shadow=False))
            self.watermark_pos = (int(W / 2 - self.watermark.width / 2), int((atop - self.watermark.height) / 2))
        elif self.hook_style == "duo":
            # one line at the very top, its answer at the bottom, photo breathing in between
            n = int(H * 0.30)
            g[:n, :, 3] = (np.linspace(1, 0, n) ** 1.2 * 200)[:, None].astype(np.uint8)
            g0 = int(H * 0.45)
            g[g0:, :, 3] = (np.clip(np.linspace(0, 1.6, H - g0), 0, 1) ** 0.8 * 235)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            d = ImageDraw.Draw(lay)
            fl = font("Playfair700.ttf", 104 * fs)
            fsub = font("Montserrat600.ttf", 40 * fs)
            top, bot = hook["lines"]
            yt = int(H * (0.15 if self.tall else 0.17))
            yb = int(H * (0.62 if self.tall else 0.60))
            parts = [(top, fl, CREAM, W / 2 - d.textlength(top, font=fl) / 2, yt, 0),
                     (bot, fl, GOLD, W / 2 - d.textlength(bot, font=fl) / 2, yb, 0),
                     (hook["sub"], fsub, CREAM, W / 2 - d.textlength(hook["sub"], font=fsub) / 2, yb + int(135 * fs), 0)]
            lay.alpha_composite(self.text_layer(parts))
            self.check_rows = [Image.new("RGBA", (W, H), (0, 0, 0, 0))]
            self.watermark_pos = (int(W / 2 - self.watermark.width / 2), int(H * 0.04))
        elif self.hook_style == "magazine":
            # magazine cover: huge masthead across the top, cover lines down the left
            n = int(H * 0.36)
            g[:n, :, 3] = (np.linspace(1, 0, n) * 170)[:, None].astype(np.uint8)
            g0 = int(H * 0.42)
            g[g0:, :, 3] = (np.clip(np.linspace(0, 1.6, H - g0), 0, 1) ** 0.8 * 235)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            d = ImageDraw.Draw(lay)
            mast = hook["kicker"]
            sz = 300 * fs
            fm = font("Playfair700.ttf", sz)
            while d.textlength(mast, font=fm) > W - 2 * mx and sz > 60:
                sz -= 6
                fm = font("Playfair700.ttf", sz)
            ym = int(H * (0.12 if self.tall else 0.13))
            parts = [(mast, fm, CREAM, W / 2 - d.textlength(mast, font=fm) / 2, ym, 0)]
            fl = font("Montserrat700.ttf", 46 * fs)
            fb = font("Playfair700.ttf", 88 * fs)
            y = int(H * (0.55 if self.tall else 0.52))
            for i, line in enumerate(hook["lines"]):
                if i == 0:
                    parts.append((line, fb, GOLD, mx, y, 0))
                    y += int(115 * fs)
                else:
                    parts.append((line, fl, CREAM, mx + int(30 * fs), y, 0))
                    y += int(68 * fs)
            lay.alpha_composite(self.text_layer(parts))
            d = ImageDraw.Draw(lay)
            y0 = int(H * (0.55 if self.tall else 0.52)) + int(130 * fs)
            for i in range(len(hook["lines"]) - 1):
                cy = y0 + int(68 * fs) * i + int(28 * fs)
                d.rectangle([mx, cy - int(5 * fs), mx + int(12 * fs), cy + int(7 * fs)], fill=GOLD + (255,))
            fi = font("Montserrat600.ttf", 34 * fs)
            d.text((W - mx, ym + int(sz * 1.22)), hook["sub"], font=fi, fill=GOLD, anchor="ra")
            self.watermark_pos = (mx, int(H * 0.035))
        elif self.hook_style == "polaroid":
            # tilted instant-photo window into the moving shot, green wall around, caption on the frame
            ang = -4
            pw, ph = int(W * (0.78 if self.tall else 0.66)), int(H * (0.42 if self.tall else 0.34))
            fb = int(26 * fs)
            capb = int(150 * fs)
            cx, cy = W // 2, int(H * (0.44 if self.tall else 0.42))
            hole = Image.new("L", (pw, ph), 255)
            frame = Image.new("RGBA", (pw + 2 * fb, ph + fb + capb), CREAM + (255,))
            dF = ImageDraw.Draw(frame)
            fcap = font("Playfair700.ttf", 64 * fs)
            dF.text((frame.width / 2, ph + fb + capb / 2), hook["lines"][0], font=fcap, fill=GREEN, anchor="mm")
            fm = Image.new("L", frame.size, 255)
            ImageDraw.Draw(fm).rectangle([fb, fb, fb + pw, fb + ph], fill=0)
            frame.putalpha(fm)
            frame = frame.rotate(ang, expand=True, resample=Image.BICUBIC)
            holeL = Image.new("L", (pw + 2 * fb, ph + fb + capb), 0)
            ImageDraw.Draw(holeL).rectangle([fb, fb, fb + pw, fb + ph], fill=255)
            holeL = holeL.rotate(ang, expand=True, resample=Image.BICUBIC)
            ox, oy = cx - frame.width // 2, self.watermark_pos[1] + self.watermark.height + int(30 * fs)
            wallm = Image.new("L", (W, H), 255)
            wallm.paste(Image.eval(holeL, lambda v: 255 - v), (ox, oy), holeL)
            wall = Image.new("RGBA", (W, H), GREEN + (255,))
            wall.putalpha(wallm)
            lay.alpha_composite(wall)
            sh = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            sh.putalpha(frame.split()[3].filter(ImageFilter.GaussianBlur(14 * fs)).point(lambda v: int(v * 0.5)))
            lay.alpha_composite(sh, (ox + int(10 * fs), oy + int(16 * fs)))
            lay.alpha_composite(frame, (ox, oy))
            d = ImageDraw.Draw(lay)
            fk = font("Montserrat700.ttf", 40 * fs)
            fsub = font("Montserrat600.ttf", 42 * fs)
            yk = oy + frame.height + int(40 * fs)
            tr_ = 8 * fs
            kw = sum(d.textlength(c, font=fk) + tr_ for c in hook["kicker"]) - tr_
            lay.alpha_composite(self.text_layer([(hook["kicker"], fk, GOLD, W / 2 - kw / 2, yk, tr_),
                                                 (hook["sub"], fsub, CREAM, W / 2 - d.textlength(hook["sub"], font=fsub) / 2, yk + int(70 * fs), 0)], shadow=False))
        elif self.hook_style == "viewfinder":
            # camera viewfinder: gold corner brackets, REC dot + timer, centre crosshair, caption bottom
            d = ImageDraw.Draw(lay)
            g0 = int(H * 0.55)
            g[g0:, :, 3] = (np.clip(np.linspace(0, 1.4, H - g0), 0, 1) * 200)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            d = ImageDraw.Draw(lay)
            m, L, lw = int(56 * fs), int(120 * fs), max(3, int(7 * fs))
            top, bot = int(H * (0.14 if self.tall else 0.17)), int(H * (0.56 if self.tall else 0.50))
            for (x, y, sx, sy) in [(m, top, 1, 1), (W - m, top, -1, 1), (m, bot, 1, -1), (W - m, bot, -1, -1)]:
                d.line([(x, y), (x + sx * L, y)], fill=CREAM + (255,), width=lw)
                d.line([(x, y), (x, y + sy * L)], fill=CREAM + (255,), width=lw)
            cx, cy = W // 2, (top + bot) // 2
            d.line([(cx - 34 * fs, cy), (cx + 34 * fs, cy)], fill=CREAM + (200,), width=max(2, int(3 * fs)))
            d.line([(cx, cy - 34 * fs), (cx, cy + 34 * fs)], fill=CREAM + (200,), width=max(2, int(3 * fs)))
            self.rec_pos = (m + int(30 * fs), top + int(40 * fs))
            fr = font("Montserrat700.ttf", 40 * fs)
            d.text((self.rec_pos[0] + int(44 * fs), self.rec_pos[1]), "CANLI BAXIŞ", font=fr, fill=WHITE, anchor="lm")
            fl = font("Playfair700.ttf", 98 * fs)
            fsub = font("Montserrat600.ttf", 42 * fs)
            y = bot + int(36 * fs)
            parts = []
            for i, line in enumerate(hook["lines"]):
                parts.append((line, fl, CREAM if i == 0 else GOLD, mx, y, 0))
                y += int(112 * fs)
            parts.append((hook["sub"], fsub, CREAM, mx, y + int(6 * fs), 0))
            lay.alpha_composite(self.text_layer(parts))
            self.watermark_pos = (W - self.watermark.width - m - int(20 * fs), top + int(16 * fs))
        elif self.hook_style == "news":
            # breaking-news lower third: gold "SON DƏQİQƏ" tab, green bar with headline, cream ticker strip
            d = ImageDraw.Draw(lay)
            g0 = int(H * 0.50)
            g[g0:, :, 3] = (np.clip(np.linspace(0, 1.3, H - g0), 0, 1) * 170)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            d = ImageDraw.Draw(lay)
            y0 = int(H * (0.56 if self.tall else 0.50))
            ft = font("Montserrat700.ttf", 40 * fs)
            tab = hook["kicker"]
            tw = d.textlength(tab, font=ft)
            th = int(72 * fs)
            d.rectangle([0, y0, mx + tw + 40 * fs, y0 + th], fill=GOLD + (255,))
            d.text((mx, y0 + th / 2), tab, font=ft, fill=GREEN, anchor="lm")
            fh = font("Playfair700.ttf", 80 * fs)
            bh = int(110 * fs) * len(hook["lines"]) + int(40 * fs)
            d.rectangle([0, y0 + th, W, y0 + th + bh], fill=GREEN_DARK + (235,))
            yy = y0 + th + int(22 * fs)
            for i, line in enumerate(hook["lines"]):
                d.text((mx, yy), line, font=fh, fill=CREAM if i == 0 else GOLD)
                yy += int(110 * fs)
            ys = y0 + th + bh
            sh_ = int(64 * fs)
            d.rectangle([0, ys, W, ys + sh_], fill=CREAM + (245,))
            fsb = font("Montserrat700.ttf", 34 * fs)
            d.text((mx, ys + sh_ / 2), hook["sub"], font=fsb, fill=GREEN, anchor="lm")
        elif self.hook_style == "ticket":
            # cream admission ticket with perforated stub: "Yeni ünvan" -> place, big serif destination
            d = ImageDraw.Draw(lay)
            n = int(H * 0.30)
            g[:n, :, 3] = (np.linspace(1, 0, n) * 120)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            tw_, th_ = int(W * 0.86), int(420 * fs)
            tk = Image.new("RGBA", (tw_, th_), (0, 0, 0, 0))
            dt = ImageDraw.Draw(tk)
            r = int(34 * fs)
            dt.rounded_rectangle([0, 0, tw_, th_], radius=int(26 * fs), fill=CREAM + (250,))
            stub = int(tw_ * 0.72)
            for cy_ in (0, th_):  # notches
                dt.ellipse([stub - r, cy_ - r, stub + r, cy_ + r], fill=(0, 0, 0, 0))
            for yy in range(int(r * 1.4), th_ - int(r * 1.2), int(26 * fs)):
                dt.line([(stub, yy), (stub, yy + int(12 * fs))], fill=GREEN + (160,), width=max(2, int(3 * fs)))
            pad = int(44 * fs)
            fk = font("Montserrat700.ttf", 30 * fs)
            dt.text((pad, pad), hook["kicker"], font=fk, fill=GOLD)
            fb = font("Playfair700.ttf", 104 * fs)
            dt.text((pad, pad + int(48 * fs)), hook["lines"][0], font=fb, fill=GREEN)
            fl2 = font("Montserrat600.ttf", 36 * fs)
            yy = pad + int(190 * fs)
            for line in hook["lines"][1:]:
                dt.text((pad, yy), line, font=fl2, fill=GREEN)
                yy += int(52 * fs)
            fs2 = font("Montserrat700.ttf", 28 * fs)
            sx = stub + (tw_ - stub) / 2
            dt.text((sx, th_ * 0.30), "GİRİŞ", font=fs2, fill=GOLD, anchor="mm")
            dt.text((sx, th_ * 0.52), hook["sub"], font=font("Playfair700.ttf", 72 * fs), fill=GREEN, anchor="mm")
            dt.text((sx, th_ * 0.72), "AÇIQDIR", font=fs2, fill=GOLD, anchor="mm")
            tk = tk.rotate(3, expand=True, resample=Image.BICUBIC)
            ox, oy = W // 2 - tk.width // 2, int(H * (0.50 if self.tall else 0.42))
            shd = Image.new("RGBA", tk.size, (0, 0, 0, 0))
            shd.putalpha(tk.split()[3].filter(ImageFilter.GaussianBlur(18 * fs)).point(lambda v: int(v * 0.55)))
            lay.alpha_composite(shd, (ox + int(8 * fs), oy + int(18 * fs)))
            lay.alpha_composite(tk, (ox, oy))
        elif self.hook_style == "pin":
            # map-style location pin + dotted route "100 m" to a road marker, title under it
            g0 = int(H * 0.48)
            g[g0:, :, 3] = (np.clip(np.linspace(0, 1.4, H - g0), 0, 1) * 215)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            d = ImageDraw.Draw(lay)
            py = int(H * (0.56 if self.tall else 0.50))
            px = mx + int(60 * fs)
            R = int(46 * fs)
            d.ellipse([px - R, py - 2 * R, px + R, py], fill=GOLD + (255,))
            d.polygon([(px - R * 0.72, py - R * 0.5), (px + R * 0.72, py - R * 0.5), (px, py + R * 0.9)], fill=GOLD + (255,))
            d.ellipse([px - R * 0.4, py - R * 1.4, px + R * 0.4, py - R * 0.6], fill=GREEN + (255,))
            rx = W - mx - int(60 * fs)
            for x in range(int(px + R * 1.6), int(rx - R), int(34 * fs)):
                d.ellipse([x, py - 7 * fs, x + 14 * fs, py + 7 * fs], fill=CREAM + (255,))
            d.rounded_rectangle([rx - R * 0.9, py - R * 0.9, rx + R * 0.9, py + R * 0.9], radius=int(10 * fs), fill=CREAM + (255,))
            d.rectangle([rx - R * 0.12, py - R * 0.6, rx + R * 0.12, py + R * 0.6], fill=GREEN + (255,))
            fk = font("Montserrat700.ttf", 44 * fs)
            d.text(((px + rx) / 2, py - int(62 * fs)), hook["kicker"], font=fk, fill=CREAM, anchor="mm")
            fl = font("Playfair700.ttf", 96 * fs)
            fsub = font("Montserrat600.ttf", 42 * fs)
            y = py + int(80 * fs)
            parts = []
            for i, line in enumerate(hook["lines"]):
                parts.append((line, fl, CREAM if i == 0 else GOLD, mx, y, 0))
                y += int(110 * fs)
            parts.append((hook["sub"], fsub, CREAM, mx, y + int(6 * fs), 0))
            lay.alpha_composite(self.text_layer(parts))
        elif self.hook_style == "chat":
            # DM chat: question bubble (cream, left) -> answer bubble (green, right), pop in one by one
            n = int(H * 0.30)
            g[:n, :, 3] = (np.linspace(1, 0, n) * 120)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            self.check_rows = []
            y = int(H * (0.36 if self.tall else 0.28))
            f_ = font("Montserrat700.ttf", 50 * fs)
            for j, line in enumerate(hook["lines"]):
                L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                dl = ImageDraw.Draw(L)
                me = j % 2 == 1
                words, rows_, cur = line.split(), [], ""
                for w_ in words:
                    if dl.textlength((cur + " " + w_).strip(), font=f_) > W * 0.62:
                        rows_.append(cur); cur = w_
                    else:
                        cur = (cur + " " + w_).strip()
                rows_.append(cur)
                tw = max(dl.textlength(r, font=f_) for r in rows_)
                bh = int(66 * fs) * len(rows_) + int(44 * fs)
                bw = tw + int(70 * fs)
                x0 = W - mx - bw if me else mx
                fill = GREEN_DARK + (240,) if me else CREAM + (245,)
                dl.rounded_rectangle([x0, y, x0 + bw, y + bh], radius=int(36 * fs), fill=fill)
                tail = [(x0 + bw - 30 * fs, y + bh - 4), (x0 + bw + 18 * fs, y + bh + 14 * fs), (x0 + bw - 70 * fs, y + bh - 4)] if me else \
                       [(x0 + 30 * fs, y + bh - 4), (x0 - 18 * fs, y + bh + 14 * fs), (x0 + 70 * fs, y + bh - 4)]
                dl.polygon(tail, fill=fill)
                for k, r in enumerate(rows_):
                    dl.text((x0 + 35 * fs, y + int(22 * fs) + k * int(66 * fs)), r, font=f_, fill=CREAM if me else GREEN)
                self.check_rows.append(L)
                y += bh + int(46 * fs)
            fk = font("Montserrat600.ttf", 32 * fs)
            dk = ImageDraw.Draw(lay)
            ky = int(H * (0.36 if self.tall else 0.28)) - int(60 * fs)
            kw = dk.textlength(hook["kicker"], font=fk)
            dk.rounded_rectangle([W / 2 - kw / 2 - 24 * fs, ky - 26 * fs, W / 2 + kw / 2 + 24 * fs, ky + 26 * fs], radius=int(26 * fs), fill=(0, 0, 0, 120))
            dk.text((W / 2, ky), hook["kicker"], font=fk, fill=CREAM, anchor="mm")
        elif self.hook_style == "triptych":
            # three vertical photo strips (hook photo + extra photos) with gold gutters, title band
            keys = [self.shots[0][0]] + hook.get("extra", [])
            sw = W // 3
            for j, k in enumerate(keys[:3]):
                im = load_photo(k)
                iw, ih = im.size
                ar = sw / H
                cw, ch = (ih * ar, ih) if iw / ih > ar else (iw, iw / ar)
                x0 = (iw - cw) / 2
                strip = im.resize((sw, H), Image.BICUBIC, box=(x0, (ih - ch) / 2, x0 + cw, (ih + ch) / 2)).convert("RGBA")
                lay.alpha_composite(strip, (j * sw, 0))
            d = ImageDraw.Draw(lay)
            gw = max(4, int(8 * fs))
            for j in (1, 2):
                d.rectangle([j * sw - gw // 2, 0, j * sw + gw // 2, H], fill=GOLD + (255,))
            by = int(H * (0.50 if self.tall else 0.45))
            bh = int(300 * fs)
            d.rectangle([0, by, W, by + bh], fill=GREEN_DARK + (230,))
            d.rectangle([0, by, W, by + max(3, int(5 * fs))], fill=GOLD + (255,))
            d.rectangle([0, by + bh - max(3, int(5 * fs)), W, by + bh], fill=GOLD + (255,))
            fk = font("Montserrat700.ttf", 38 * fs)
            fl = font("Playfair700.ttf", 92 * fs)
            tr_ = 8 * fs
            kw = sum(d.textlength(c, font=fk) + tr_ for c in hook["kicker"]) - tr_
            parts = [(hook["kicker"], fk, GOLD, W / 2 - kw / 2, by + int(40 * fs), tr_)]
            yy = by + int(100 * fs)
            for line in hook["lines"]:
                parts.append((line, fl, CREAM, W / 2 - d.textlength(line, font=fl) / 2, yy, 0))
                yy += int(100 * fs)
            lay.alpha_composite(self.text_layer(parts, shadow=False))
        elif self.hook_style == "blueprint":
            # architect's drawing: faint grid, dimension line, technical title block
            d = ImageDraw.Draw(lay)
            step = int(90 * fs)
            for x in range(0, W, step):
                d.line([(x, 0), (x, H)], fill=CREAM + (34,), width=1)
            for y in range(0, H, step):
                d.line([(0, y), (W, y)], fill=CREAM + (34,), width=1)
            g0 = int(H * 0.46)
            g[g0:, :, 3] = (np.clip(np.linspace(0, 1.5, H - g0), 0, 1) * 190)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            d = ImageDraw.Draw(lay)
            lw = max(2, int(3 * fs))
            yd = int(H * (0.43 if self.tall else 0.40))
            x0d, x1d = mx, W - mx
            d.line([(x0d, yd), (x1d, yd)], fill=CREAM + (255,), width=lw)
            for xx_ in (x0d, x1d):
                d.line([(xx_, yd - 22 * fs), (xx_, yd + 22 * fs)], fill=CREAM + (255,), width=lw)
                sgn = 1 if xx_ == x0d else -1
                d.polygon([(xx_, yd), (xx_ + sgn * 26 * fs, yd - 10 * fs), (xx_ + sgn * 26 * fs, yd + 10 * fs)], fill=CREAM + (255,))
            fdm = font("Montserrat700.ttf", 40 * fs)
            dt = hook["kicker"]
            tw = d.textlength(dt, font=fdm)
            d.rectangle([W / 2 - tw / 2 - 24 * fs, yd - 32 * fs, W / 2 + tw / 2 + 24 * fs, yd + 32 * fs], fill=GREEN_DARK + (255,))
            d.text((W / 2, yd), dt, font=fdm, fill=GOLD, anchor="mm")
            # title block
            by = yd + int(90 * fs)
            fl = font("Playfair700.ttf", 84 * fs)
            fc = font("Montserrat600.ttf", 34 * fs)
            fsmall = font("Montserrat700.ttf", 26 * fs)
            rows_h = [int(56 * fs)] + [int(100 * fs)] * len(hook["lines"]) + [int(86 * fs)]
            bh = sum(rows_h)
            d.rectangle([mx, by, W - mx, by + bh], fill=GREEN_DARK + (225,), outline=CREAM + (255,), width=lw)
            y = by
            d.text((mx + 26 * fs, y + rows_h[0] / 2), "LAYİHƏ", font=fsmall, fill=GOLD, anchor="lm")
            d.text((W - mx - 26 * fs, y + rows_h[0] / 2), "VƏRƏQ 01", font=fsmall, fill=GOLD, anchor="rm")
            y += rows_h[0]
            for i, line in enumerate(hook["lines"]):
                d.line([(mx, y), (W - mx, y)], fill=CREAM + (200,), width=max(1, lw // 2))
                d.text((mx + 26 * fs, y + rows_h[1 + i] / 2), line, font=fl, fill=CREAM if i == 0 else GOLD, anchor="lm")
                y += rows_h[1 + i]
            d.line([(mx, y), (W - mx, y)], fill=CREAM + (200,), width=max(1, lw // 2))
            cells = [c.strip() for c in hook["sub"].split("•")]
            cw_ = (W - 2 * mx) / len(cells)
            for j, ctext in enumerate(cells):
                if j:
                    d.line([(mx + j * cw_, y), (mx + j * cw_, y + rows_h[-1])], fill=CREAM + (200,), width=max(1, lw // 2))
                d.text((mx + j * cw_ + cw_ / 2, y + rows_h[-1] / 2), ctext, font=fc, fill=CREAM, anchor="mm")
        elif self.hook_style == "seal":
            # gold rosette seal with serrated edge, words around a big centre word, title under it
            g0 = int(H * 0.40)
            g[g0:, :, 3] = (np.clip(np.linspace(0, 1.5, H - g0), 0, 1) * 205)[:, None].astype(np.uint8)
            n = int(H * 0.22)
            g[:n, :, 3] = np.maximum(g[:n, :, 3], (np.linspace(1, 0, n) * 110)[:, None].astype(np.uint8))
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            R = int(200 * fs)
            S = 2 * R + 40
            sl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
            ds = ImageDraw.Draw(sl)
            c = S / 2
            pts = []
            for k in range(72):
                rr = R if k % 2 == 0 else R * 0.93
                a_ = k * math.pi / 36
                pts.append((c + rr * math.cos(a_), c + rr * math.sin(a_)))
            ds.polygon(pts, fill=GOLD + (255,))
            ds.ellipse([c - R * 0.84, c - R * 0.84, c + R * 0.84, c + R * 0.84], fill=GREEN + (255,))
            ds.ellipse([c - R * 0.78, c - R * 0.78, c + R * 0.78, c + R * 0.78], outline=GOLD + (255,), width=max(2, int(3 * fs)))
            top, mid, bot = hook["seal"]
            ds.text((c, c - R * 0.40), top, font=font("Montserrat700.ttf", 34 * fs), fill=GOLD, anchor="mm")
            fm_ = font("Playfair700.ttf", 104 * fs)
            while ds.textlength(mid, font=fm_) > R * 1.4:
                fm_ = font("Playfair700.ttf", fm_.size - 4)
            ds.text((c, c + 4 * fs), mid, font=fm_, fill=CREAM, anchor="mm")
            ds.text((c, c + R * 0.42), bot, font=font("Montserrat700.ttf", 34 * fs), fill=GOLD, anchor="mm")
            sl = sl.rotate(-8, resample=Image.BICUBIC)
            sy = int(H * (0.15 if self.tall else 0.10))
            shd = Image.new("RGBA", sl.size, (0, 0, 0, 0))
            shd.putalpha(sl.split()[3].filter(ImageFilter.GaussianBlur(16 * fs)).point(lambda v: int(v * 0.5)))
            lay.alpha_composite(shd, (W // 2 - S // 2 + 8, sy + 14))
            lay.alpha_composite(sl, (W // 2 - S // 2, sy))
            d = ImageDraw.Draw(lay)
            fl = font("Playfair700.ttf", 96 * fs)
            fsub = font("Montserrat600.ttf", 42 * fs)
            y = sy + S + int(30 * fs)
            parts = []
            for i, line in enumerate(hook["lines"]):
                parts.append((line, fl, CREAM if i == 0 else GOLD, W / 2 - d.textlength(line, font=fl) / 2, y, 0))
                y += int(110 * fs)
            parts.append((hook["sub"], fsub, CREAM, W / 2 - d.textlength(hook["sub"], font=fsub) / 2, y + int(6 * fs), 0))
            lay.alpha_composite(self.text_layer(parts))
            self.watermark_pos = (int(W / 2 - self.watermark.width / 2), int(H * 0.025))
        elif self.hook_style == "callout":
            # dots on the photo with leader lines to small labels, title band at the bottom
            g0 = int(H * 0.58)
            g[g0:, :, 3] = (np.clip(np.linspace(0, 1.4, H - g0), 0, 1) * 215)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            d = ImageDraw.Draw(lay)
            fcl = font("Montserrat700.ttf", 38 * fs)
            lw = max(2, int(3 * fs))
            for fx, fy, side, text in hook["callouts"]:
                px, py = fx * W, fy * H
                lx = mx if side == "l" else W - mx
                ly = py - int(90 * fs)
                ex = px + (-1 if side == "l" else 1) * int(110 * fs)
                d.line([(px, py), (ex, ly), (lx + (1 if side == "l" else -1) * 0, ly)], fill=CREAM + (255,), width=lw)
                r_ = int(13 * fs)
                d.ellipse([px - r_ - 6 * fs, py - r_ - 6 * fs, px + r_ + 6 * fs, py + r_ + 6 * fs], outline=GOLD + (255,), width=lw)
                d.ellipse([px - r_ * 0.6, py - r_ * 0.6, px + r_ * 0.6, py + r_ * 0.6], fill=GOLD + (255,))
                tw = d.textlength(text, font=fcl)
                bh = int(66 * fs)
                bx0 = lx if side == "l" else lx - tw - 44 * fs
                d.rounded_rectangle([bx0, ly - bh, bx0 + tw + 44 * fs, ly], radius=int(12 * fs), fill=GREEN_DARK + (235,))
                d.text((bx0 + 22 * fs, ly - bh / 2), text, font=fcl, fill=CREAM, anchor="lm")
            fl = font("Playfair700.ttf", 96 * fs)
            fsub = font("Montserrat600.ttf", 42 * fs)
            y = int(H * (0.62 if self.tall else 0.60))
            parts = []
            for i, line in enumerate(hook["lines"]):
                parts.append((line, fl, CREAM if i == 0 else GOLD, mx, y, 0))
                y += int(110 * fs)
            parts.append((hook["sub"], fsub, CREAM, mx, y + int(6 * fs), 0))
            lay.alpha_composite(self.text_layer(parts))
        elif self.hook_style == "postcard":
            # cream postcard with photo window, stamp and postmark
            d = ImageDraw.Draw(lay)
            n = int(H * 0.25)
            g[:n, :, 3] = (np.linspace(1, 0, n) * 110)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            cw_, ch_ = W - 2 * mx, int(H * (0.30 if self.tall else 0.34))
            cy0 = int(H * (0.43 if self.tall else 0.33))
            card = Image.new("RGBA", (cw_, ch_), CREAM + (250,))
            dc = ImageDraw.Draw(card)
            pad = int(30 * fs)
            dc.rectangle([pad // 2, pad // 2, cw_ - pad // 2, ch_ - pad // 2], outline=GOLD + (255,), width=max(2, int(3 * fs)))
            sx0 = int(cw_ * 0.60)
            dc.line([(sx0, pad * 2), (sx0, ch_ - pad * 2)], fill=GREEN + (120,), width=max(1, int(2 * fs)))
            fk = font("Montserrat700.ttf", 28 * fs)
            dc.text((pad * 2, pad * 2), hook["kicker"], font=fk, fill=GOLD)
            fl = font("Playfair700.ttf", 74 * fs)
            y = pad * 2 + int(52 * fs)
            for i, line in enumerate(hook["lines"]):
                dc.text((pad * 2, y), line, font=fl, fill=GREEN if i == 0 else GOLD)
                y += int(86 * fs)
            fsub = font("Montserrat600.ttf", 30 * fs)
            for k, line in enumerate(hook["sub"].split("•")):
                yy = ch_ - pad * 2 - int(46 * fs) * (len(hook["sub"].split("•")) - k)
                dc.text((sx0 + pad, yy + int(14 * fs)), line.strip(), font=fsub, fill=GREEN)
                dc.line([(sx0 + pad, yy + int(46 * fs)), (cw_ - pad * 2, yy + int(46 * fs))], fill=GREEN + (90,), width=1)
            stw, sth = int(130 * fs), int(150 * fs)
            stx, sty = cw_ - pad * 2 - stw, pad * 2
            for k in range(0, stw, int(14 * fs)):
                dc.ellipse([stx + k, sty - 5 * fs, stx + k + 10 * fs, sty + 5 * fs], fill=CREAM)
            dc.rectangle([stx, sty, stx + stw, sty + sth], fill=GREEN + (255,))
            dc.rectangle([stx + 8 * fs, sty + 8 * fs, stx + stw - 8 * fs, sty + sth - 8 * fs], outline=GOLD + (255,), width=max(2, int(2 * fs)))
            dc.text((stx + stw / 2, sty + sth / 2), hook["stamp"], font=font("Playfair700.ttf", 34 * fs), fill=GOLD, anchor="mm")
            pm = Image.new("RGBA", (int(230 * fs), int(230 * fs)), (0, 0, 0, 0))
            dp = ImageDraw.Draw(pm)
            c = pm.width / 2
            dp.ellipse([8, 8, pm.width - 8, pm.height - 8], outline=GREEN + (150,), width=max(2, int(3 * fs)))
            dp.text((c, c), hook["postmark"], font=font("Montserrat700.ttf", 26 * fs), fill=GREEN + (170,), anchor="mm")
            for k in range(4):
                yy = c - 40 * fs + k * 26 * fs
                dp.line([(pm.width - 4, yy), (pm.width + 140 * fs, yy)], fill=GREEN + (120,), width=2)
            pm = pm.rotate(-14, resample=Image.BICUBIC)
            card.alpha_composite(pm, (sx0 + int(20 * fs), sty + int(20 * fs)))
            card = card.rotate(-2.5, expand=True, resample=Image.BICUBIC)
            shd = Image.new("RGBA", card.size, (0, 0, 0, 0))
            shd.putalpha(card.split()[3].filter(ImageFilter.GaussianBlur(18 * fs)).point(lambda v: int(v * 0.5)))
            ox = W // 2 - card.width // 2
            lay.alpha_composite(shd, (ox + 8, cy0 + 16))
            lay.alpha_composite(card, (ox, cy0))
        elif self.hook_style == "diagonal":
            # second photo cut in on a diagonal with a gold seam; title on the seam
            ex = load_photo(hook["second"])
            iw, ih = ex.size
            ar = W / H
            cw, ch = (ih * ar, ih) if iw / ih > ar else (iw, iw / ar)
            ex = ex.resize((W, H), Image.BICUBIC, box=((iw - cw) / 2, (ih - ch) / 2, (iw + cw) / 2, (ih + ch) / 2)).convert("RGBA")
            ya, yb = int(H * (0.50 if self.tall else 0.46)), int(H * (0.66 if self.tall else 0.70))
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).polygon([(0, yb), (W, ya), (W, H), (0, H)], fill=255)
            sh_ = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sh_.alpha_composite(ex, (0, int(H * 0.30)))  # show the photo's middle in the lower half
            ex = sh_
            ex.putalpha(Image.fromarray(np.minimum(np.asarray(m), np.asarray(ex.split()[3]))))
            lay.alpha_composite(ex)
            d = ImageDraw.Draw(lay)
            d.line([(0, yb), (W, ya)], fill=GOLD + (255,), width=max(6, int(12 * fs)))
            fl = font("Playfair700.ttf", 92 * fs)
            fk = font("Montserrat700.ttf", 36 * fs)
            # labels on each half
            for txt, x, y, anc in ((hook["top"], mx, ya - int(150 * fs), "la"), (hook["bottom"], W - mx, yb + int(60 * fs), "ra")):
                tw = d.textlength(txt, font=fk)
                bx0 = x if anc == "la" else x - tw - 40 * fs
                d.rounded_rectangle([bx0, y, bx0 + tw + 40 * fs, y + 64 * fs], radius=int(32 * fs), fill=GREEN_DARK + (230,))
                d.text((bx0 + 20 * fs, y + 32 * fs), txt, font=fk, fill=CREAM, anchor="lm")
            n = int(H * 0.40)
            gg = np.zeros((H, W, 4), np.uint8)
            gg[:n, :, 3] = (np.linspace(1, 0, n) ** 1.1 * 190)[:, None].astype(np.uint8)
            top = Image.fromarray(gg, "RGBA")
            top.alpha_composite(lay)
            lay = top
            parts = []
            y = int(H * (0.16 if self.tall else 0.18))
            for i, line in enumerate(hook["lines"]):
                parts.append((line, fl, CREAM if i == 0 else GOLD, mx, y, 0))
                y += int(106 * fs)
            parts.append((hook["sub"], font("Montserrat600.ttf", 40 * fs), CREAM, mx, y + int(6 * fs), 0))
            lay.alpha_composite(self.text_layer(parts))
            self.watermark_pos = (W - self.watermark.width - int(60 * W / 1080), int(H * 0.035))
        elif self.hook_style == "spotlight":
            # dark stage, soft spotlight ellipse on the subject, centred serif title, gold numbers row
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            cx, cy = hook.get("spot", [0.5, 0.55])
            rx, ry = W * 0.55, H * 0.30
            r = np.sqrt(((xx - cx * W) / rx) ** 2 + ((yy - cy * H) / ry) ** 2)
            a = (np.clip((r - 0.7) / 0.6, 0, 1) * 215).astype(np.uint8)
            g[..., 3] = a
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            d = ImageDraw.Draw(lay)
            fl = font("Playfair700.ttf", 100 * fs)
            fk = font("Montserrat700.ttf", 34 * fs)
            y = int(H * (0.13 if self.tall else 0.15))
            tr_ = 10 * fs
            kw = sum(d.textlength(c, font=fk) + tr_ for c in hook["kicker"]) - tr_
            parts = [(hook["kicker"], fk, GOLD, W / 2 - kw / 2, y, tr_)]
            y += int(64 * fs)
            for i, line in enumerate(hook["lines"]):
                parts.append((line, fl, CREAM if i == 0 else GOLD, W / 2 - d.textlength(line, font=fl) / 2, y, 0))
                y += int(112 * fs)
            lay.alpha_composite(self.text_layer(parts))
            d = ImageDraw.Draw(lay)
            nums = hook["nums"]
            yb = int(H * (0.72 if self.tall else 0.70))
            cw_ = (W - 2 * mx) / len(nums)
            fn = font("Playfair700.ttf", 78 * fs)
            fu = font("Montserrat600.ttf", 28 * fs)
            for j, (num, unit) in enumerate(nums):
                cx_ = mx + cw_ * j + cw_ / 2
                d.text((cx_, yb), num, font=fn, fill=GOLD, anchor="mm")
                d.text((cx_, yb + 62 * fs), unit, font=fu, fill=CREAM, anchor="mm")
                if j:
                    d.line([(mx + cw_ * j, yb - 40 * fs), (mx + cw_ * j, yb + 80 * fs)], fill=CREAM + (120,), width=max(1, int(2 * fs)))
            self.watermark_pos = (int(W / 2 - self.watermark.width / 2), int(H * 0.03))
        elif self.hook_style == "plaque":
            # museum label: small cream plaque bottom-right like an artwork caption
            g0 = int(H * 0.55)
            g[g0:, :, 3] = (np.clip(np.linspace(0, 1.3, H - g0), 0, 1) * 150)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            pw = int(W * 0.66)
            ph = int(400 * fs)
            px0, py0 = W - mx - pw, int(H * (0.53 if self.tall else 0.40))
            pl = Image.new("RGBA", (pw, ph), CREAM + (248,))
            dp = ImageDraw.Draw(pl)
            pad = int(40 * fs)
            dp.text((pad, pad), hook["kicker"], font=font("Montserrat700.ttf", 26 * fs), fill=GOLD)
            y = pad + int(46 * fs)
            for i, line in enumerate(hook["lines"]):
                dp.text((pad, y), line, font=font("Playfair700.ttf", 64 * fs), fill=GREEN)
                y += int(76 * fs)
            dp.line([(pad, y + 10 * fs), (pad + 70 * fs, y + 10 * fs)], fill=GOLD, width=max(2, int(3 * fs)))
            y += int(34 * fs)
            for line in hook["sub"].split("|"):
                dp.text((pad, y), line.strip(), font=font("Montserrat600.ttf", 28 * fs), fill=GREEN + (210,))
                y += int(40 * fs)
            shd = Image.new("RGBA", pl.size, (0, 0, 0, 0))
            shd.putalpha(Image.new("L", pl.size, 150).filter(ImageFilter.GaussianBlur(4)))
            sh2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sh2.alpha_composite(shd, (px0 + 10, py0 + 14))
            lay.alpha_composite(sh2.filter(ImageFilter.GaussianBlur(16 * fs)))
            lay.alpha_composite(pl, (px0, py0))
        elif self.hook_style == "stack":
            # giant stacked words filling the width, alternating cream/gold, thin rules between
            g0 = int(H * 0.30)
            g[g0:, :, 3] = (np.clip(np.linspace(0, 1.6, H - g0), 0, 1) * 200)[:, None].astype(np.uint8)
            lay.alpha_composite(Image.fromarray(g, "RGBA"))
            d = ImageDraw.Draw(lay)
            y = int(H * (0.40 if self.tall else 0.30))
            parts = []
            rules = []
            for i, word in enumerate(hook["lines"]):
                sz = 260 * fs
                f_ = font("Montserrat700.ttf", sz)
                while d.textlength(word, font=f_) > W - 2 * mx and sz > 40:
                    sz -= 6
                    f_ = font("Montserrat700.ttf", sz)
                bb = d.textbbox((0, 0), word, font=f_)
                parts.append((word, f_, CREAM if i % 2 == 0 else GOLD, mx - bb[0], y - bb[1], 0))
                y += bb[3] - bb[1] + int(24 * fs)
                rules.append(y - int(12 * fs))
            lay.alpha_composite(self.text_layer(parts))
            d = ImageDraw.Draw(lay)
            for ry in rules[:-1]:
                d.line([(mx, ry), (W - mx, ry)], fill=CREAM + (150,), width=max(1, int(2 * fs)))
            d.text((mx, y + int(10 * fs)), hook["sub"], font=font("Montserrat600.ttf", 40 * fs), fill=CREAM)
        elif self.hook_style == "lens":
            # round magnifier showing a second photo's detail, gold ring + handle, caption beside it
            ex = load_photo(hook["second"])
            R = int(W * 0.30)
            fx, fy, z = hook.get("focus", [0.5, 0.5, 1.0])
            iw, ih = ex.size
            side = min(iw, ih) / z
            box = (fx * iw - side / 2, fy * ih - side / 2, fx * iw + side / 2, fy * ih + side / 2)
            disc = ex.resize((2 * R, 2 * R), Image.BICUBIC, box=box).convert("RGBA")
            m = Image.new("L", (2 * R, 2 * R), 0)
            ImageDraw.Draw(m).ellipse([0, 0, 2 * R - 1, 2 * R - 1], fill=255)
            disc.putalpha(m)
            cx, cy = int(W * 0.60), int(H * (0.42 if self.tall else 0.40))
            sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(sh).ellipse([cx - R + 10, cy - R + 18, cx + R + 10, cy + R + 18], fill=(0, 0, 0, 140))
            lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18 * fs)))
            lay.alpha_composite(disc, (cx - R, cy - R))
            d = ImageDraw.Draw(lay)
            rw = max(8, int(16 * fs))
            d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=GOLD + (255,), width=rw)
            a_ = math.radians(135)
            x1, y1 = cx + R * math.cos(a_), cy + R * math.sin(a_)
            d.line([(x1, y1), (x1 - 150 * fs, y1 + 150 * fs)], fill=GOLD + (255,), width=int(rw * 1.8))
            g0 = int(H * 0.62)
            gg = np.zeros((H, W, 4), np.uint8)
            gg[g0:, :, 3] = (np.clip(np.linspace(0, 1.3, H - g0), 0, 1) * 200)[:, None].astype(np.uint8)
            base = Image.fromarray(gg, "RGBA")
            base.alpha_composite(lay)
            lay = base
            fl = font("Playfair700.ttf", 92 * fs)
            y = int(H * (0.66 if self.tall else 0.66))
            parts = [(hook["kicker"], font("Montserrat700.ttf", 34 * fs), GOLD, mx, y - int(54 * fs), 8 * fs)]
            for i, line in enumerate(hook["lines"]):
                parts.append((line, fl, CREAM if i == 0 else GOLD, mx, y, 0))
                y += int(104 * fs)
            lay.alpha_composite(self.text_layer(parts))
        self.hook_v2 = lay

    def build_endcard(self, logo):
        W, H, fs = self.W, self.H, self.fs
        bg = self.kb(self.shots[0][0], self.shots[0][2], 0.0, focus=self.focus[0]).filter(ImageFilter.GaussianBlur(28))
        bg = Image.blend(bg, Image.new("RGB", bg.size, GREEN), 0.80).convert("RGBA")
        self.end_bg = bg

        cx = W / 2
        d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        items = []  # (layer, appear_time)

        def centered(text, f, fill, y, track=0):
            w = sum(d.textlength(c, font=f) + track for c in text) - track
            return (text, f, fill, cx - w / 2, y, track)

        y = H * (0.17 if self.tall else 0.08)
        lw = int(W * 0.70)
        lg = logo.resize((lw, int(lw * logo.height / logo.width)), Image.LANCZOS)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lay.alpha_composite(lg, (int(cx - lw / 2), int(y)))
        items.append((lay, 0.0))
        y += lg.height + 60 * fs

        items.append((self.text_layer([centered(T("sold", "SATILIR"), font("Montserrat700.ttf", 40 * fs), GOLD, y, 14 * fs)], False), 0.15))
        y += 70 * fs
        if self.verified is not None:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            lay.alpha_composite(self.verified, (int(cx - self.verified.width / 2), int(y - 10 * fs)))
            items.append((lay, 0.2))
            y += self.verified.height + 20 * fs
        if LISTING.get("comment_cta"):
            return self.build_endcard_v2(items, centered, y, cx)
        if not LISTING.get("price"):  # no price given: invite a call instead
            fq = font("Playfair700.ttf", 92 * fs)
            items.append((self.text_layer([centered(T("call_price", "Qiymət üçün zəng edin"), fq, GOLD, y + 40 * fs)], False), 0.3))
            y += 230 * fs
        # price: Playfair digits + Montserrat manat sign
        fp = font("Playfair700.ttf", 160 * fs)
        fm = font("Montserrat700.ttf", 120 * fs)
        if LISTING.get("price"):
            num, cur = LISTING["price"] + " ", "₼"
            wn, wc = d.textlength(num, font=fp), d.textlength(cur, font=fm)
            x0 = cx - (wn + wc) / 2
            base = y + fp.getmetrics()[0]
            lay = self.text_layer([(num, fp, GOLD, x0, y, 0),
                                   (cur, fm, GOLD, x0 + wn, base - fm.getmetrics()[0], 0)], False)
            items.append((lay, 0.3))
            y += 230 * fs

        fd = font("Montserrat600.ttf", 44 * fs)
        for i, line in enumerate(LISTING["details"]):
            items.append((self.text_layer([centered(line, fd, CREAM, y, 0)], False), 0.5 + 0.1 * i))
            y += 70 * fs
        y += 45 * fs

        # phone pill
        fph = font("Montserrat700.ttf", 64 * fs)
        phone = LISTING["phone"].replace("-", " ")  # end card shows "010 310 03 02"
        tw = d.textlength(phone, font=fph)
        ph = int(118 * fs)
        pw = tw + 110 * fs
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dd = ImageDraw.Draw(lay)
        dd.rounded_rectangle([cx - pw / 2, y, cx + pw / 2, y + ph], radius=ph // 2, fill=GOLD + (255,))
        bb = fph.getbbox(phone)
        dd.text((cx - tw / 2, y + (ph - (bb[3] - bb[1])) / 2 - bb[1]), phone, font=fph, fill=GREEN)
        items.append((lay, 0.85))
        y += ph + 40 * fs
        items.append((self.text_layer([centered(T("contact", "Zəng et  •  WhatsApp  •  DM yaz"), font("Montserrat600.ttf", 38 * fs), CREAM, y)], False), 1.0))
        self.end_items = items

    def build_endcard_v2(self, items, centered, y, cx):
        """End card without price or phone (user rules): details, share line, comment prompt."""
        W, H, fs = self.W, self.H, self.fs
        d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        y += 20 * fs
        fd = font("Montserrat600.ttf", 44 * fs)
        for i, line in enumerate(LISTING["details"]):
            items.append((self.text_layer([centered(line, fd, CREAM, y, 0)], False), 0.3 + 0.1 * i))
            y += 70 * fs
        y += 40 * fs
        if "comment_q" not in (LISTING.get("text") or {}):  # user rule: "EV" keyword CTA
            fq = font("Playfair700.ttf", 70 * fs)
            items.append((self.text_layer([centered(T("ev_q", EV_Q), fq, GOLD, y)], False), 0.7))
            y += 100 * fs
            fw = font("Montserrat700.ttf", 88 * fs)
            tw = d.textlength(T("ev_word", EV_WORD), font=fw)
            ph = int(140 * fs)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dd = ImageDraw.Draw(lay)
            dd.rounded_rectangle([cx - tw / 2 - 70 * fs, y, cx + tw / 2 + 70 * fs, y + ph], radius=int(28 * fs), fill=GOLD + (255,))
            dd.text((cx, y + ph / 2), T("ev_word", EV_WORD), font=fw, fill=GREEN, anchor="mm")
            items.append((lay, 0.85))
            y += ph + 26 * fs
            items.append((self.text_layer([centered(T("ev_dm", EV_DM), font("Montserrat600.ttf", 42 * fs), CREAM, y)], False), 0.95))
            y += 100 * fs
            self._endcard_share(items, centered, y, d)
            return
        fq = font("Playfair700.ttf", 78 * fs)
        items.append((self.text_layer([centered(T("comment_q", COMMENT_Q), fq, GOLD, y)], False), 0.7))
        y += 110 * fs
        fp = font("Montserrat700.ttf", 46 * fs)
        t = T("comment_a", COMMENT_A) + "  ↓"
        tw = d.textlength(t, font=fp)
        ph = int(100 * fs)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dd = ImageDraw.Draw(lay)
        dd.rounded_rectangle([cx - tw / 2 - 50 * fs, y, cx + tw / 2 + 50 * fs, y + ph], radius=ph // 2, fill=GOLD + (255,))
        dd.text((cx, y + ph / 2), t, font=fp, fill=GREEN, anchor="mm")
        items.append((lay, 0.85))
        y += ph + 60 * fs
        self._endcard_share(items, centered, y, d)

    def _endcard_share(self, items, centered, y, d):
        W, fs = self.W, self.fs
        share = LISTING.get("share")
        if share:
            fs1 = font("Montserrat700.ttf", 46 * fs)
            words, lines, cur = share.split(), [], ""
            for w_ in words:
                if d.textlength((cur + " " + w_).strip(), font=fs1) > W * 0.82:
                    lines.append(cur)
                    cur = w_
                else:
                    cur = (cur + " " + w_).strip()
            lines.append(cur)
            for j, ln in enumerate(lines):
                items.append((self.text_layer([centered(ln, fs1, WHITE, y + j * 62 * fs)], False), 1.1))
        self.end_items = items

    # ---------- compositing helpers ----------
    @staticmethod
    def fade(layer, a, dy=0):
        if a <= 0:
            return None
        lay = layer
        if a < 1:
            arr = np.asarray(layer).copy()
            arr[..., 3] = (arr[..., 3] * a).astype(np.uint8)
            lay = Image.fromarray(arr, "RGBA")
        if dy:
            shifted = Image.new("RGBA", lay.size, (0, 0, 0, 0))
            shifted.alpha_composite(lay, (0, int(dy)))
            lay = shifted
        return lay

    def hblur(self, im, s):
        if s <= 0.02:
            return im
        w = max(8, int(self.W / (1 + 45 * s)))
        return im.resize((w, self.H), Image.BILINEAR).resize((self.W, self.H), Image.BILINEAR)

    # ---------- frame generation ----------
    def shot_frame(self, i, t):
        key, dur, motion, label, tr = self.shots[i]
        punch = 0.10 * (1 - ease_out(t / TR)) if tr == "punch" and t < TR else 0.0
        return self.kb(key, motion, t / dur, punch, self.focus[i]).convert("RGBA")

    def decorate(self, im, i, t):
        key, dur, motion, label, _ = self.shots[i]
        if i == 0:
            if self.hook_style == "classic":
                im.alpha_composite(self.grad_hook)
            im.alpha_composite(self.hook)
            if self.hook_pill is not None:  # pill pulses gently
                a = 0.75 + 0.25 * math.sin(t * 2 * math.pi * 1.5)
                im.alpha_composite(self.fade(self.hook_pill, a))
            if self.hook_style == "guess":  # 5..1 countdown over the hook shot
                n = max(1, 5 - int(t / (dur / 5)))
                im.alpha_composite(self.guess_nums[n])
            if self.hook_style == "viewfinder" and int(t * 2) % 2 == 0:  # blinking REC dot
                dd = ImageDraw.Draw(im)
                x, y = self.rec_pos
                rr = int(16 * self.fs)
                dd.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(226, 54, 54, 255))
            if self.hook_style in ("checklist", "beats", "chat"):  # rows pop in one by one
                for j, row in enumerate(self.check_rows):
                    a = ease_out((t - 0.35 - 0.35 * j) / 0.25)
                    lay = self.fade(row, a, dy=20 * (1 - a))
                    if lay:
                        im.alpha_composite(lay)
        im.alpha_composite(self.watermark, self.watermark_pos)
        if i == 0 and self.verified is not None:  # "Yoxlanılmış Ev" badge under the logo on the hook
            x, y = self.watermark_pos
            im.alpha_composite(self.verified, (x, y + self.watermark.height + int(18 * self.fs)))
        if label:
            a_in = ease_out((t - 0.14) / 0.22)
            a_out = 1 - ease((t - (dur - 0.12)) / 0.12)
            a = min(a_in, a_out)
            lay = self.fade(self.labels[label], a, dy=30 * (1 - a_in))
            if lay:
                im.alpha_composite(lay)
        if i == 0:  # phone box only on the hook shot (user rule)
            im.alpha_composite(self.cta)
        save_i = LISTING.get("save_cta", len(self.shots) // 2)  # user rule: mid-video save prompt (false -> off)
        if save_i is not False and i > 0 and save_i == i:  # mid-video "save" prompt, pops in and pulses
            a = ease_out((t - 0.05) / 0.25) * (1 - ease((t - (dur - 0.15)) / 0.15))
            lay = self.fade(self.save_layer(), a * (0.85 + 0.15 * math.sin(t * 2 * math.pi * 2)), dy=-25 * (1 - a))
            if lay:
                im.alpha_composite(lay)
        return im

    def verified_badge(self):
        """Green pill with gold border and a gold check circle: "Xəzər Sahil — Yoxlanılmış Ev"."""
        fs = self.fs
        f = font("Montserrat700.ttf", 34 * fs)
        txt = T("verified", VERIFIED_TXT)
        tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        ph = int(76 * fs)
        r = ph * 0.32
        pw = int(ph * 0.30 + 2 * r + 22 * fs + tmp.textlength(txt, font=f) + 36 * fs)
        lay = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=ph // 2, fill=GREEN_DARK + (235,),
                            outline=GOLD + (255,), width=max(2, int(3 * fs)))
        cx, cy = ph * 0.30 + r, ph / 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD + (255,))
        d.line([(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.10, cy + r * 0.38), (cx + r * 0.50, cy - r * 0.36)],
               fill=GREEN_DARK + (255,), width=max(3, int(6 * fs)), joint="curve")
        d.text((cx + r + 22 * fs, cy), txt, font=f, fill=WHITE, anchor="lm")
        return lay

    def save_layer(self):
        if getattr(self, "_save", None) is None:
            W, H, fs = self.W, self.H, self.fs
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            f = font("Montserrat700.ttf", 50 * fs)
            tw = d.textlength(SAVE_TXT, font=f)
            ph = int(104 * fs)
            iw = int(40 * fs)
            bw = tw + iw + 40 * fs + 100 * fs
            x0, y0 = W / 2 - bw / 2, int(H * (0.40 if self.tall else 0.38))
            d.rounded_rectangle([x0, y0, x0 + bw, y0 + ph], radius=ph // 2, fill=CREAM + (245,), outline=GOLD + (255,), width=max(2, int(4 * fs)))
            bx, by, bh = x0 + 50 * fs, y0 + ph * 0.24, ph * 0.52  # bookmark icon
            d.polygon([(bx, by), (bx + iw, by), (bx + iw, by + bh), (bx + iw / 2, by + bh * 0.72), (bx, by + bh)], fill=GREEN)
            d.text((bx + iw + 30 * fs, y0 + ph / 2), SAVE_TXT, font=f, fill=GREEN, anchor="lm")
            self._save = lay
        return self._save

    def full_shot(self, i, t):
        return self.decorate(self.shot_frame(i, t), i, t)

    def end_frame(self, t):
        im = self.end_bg.copy()
        for lay, t0 in self.end_items:
            a = ease_out((t - t0) / 0.35)
            l2 = self.fade(lay, a, dy=40 * (1 - a))
            if l2:
                im.alpha_composite(l2)
        return im

    def frames(self):
        shots = self.shots
        starts, acc = [], 0.0
        for s in shots:
            starts.append(acc)
            acc += s[1]
        end_start = acc
        total = end_start + END_DUR
        first = self.full_shot(0, 0.0).convert("RGB")
        n = int(round(total * FPS))
        for fi in range(n):
            T = fi / FPS
            if T >= end_start:
                t = T - end_start
                if t < TR:  # flash in from last shot
                    prev = self.full_shot(len(shots) - 1, shots[-1][1] + t).convert("RGB")
                    fr = flash(prev, self.end_frame(t).convert("RGB"), t / TR)
                elif t > END_DUR - END_LOOP:
                    k = ease((t - (END_DUR - END_LOOP)) / END_LOOP)
                    fr = Image.blend(self.end_frame(t).convert("RGB"), first, k)
                else:
                    fr = self.end_frame(t).convert("RGB")
                yield fr
                continue
            i = max(j for j, s in enumerate(starts) if s <= T + 1e-9)
            t = T - starts[i]
            tr = shots[i][4]
            if tr in ("whip", "flash", "slide", "fade", "zoom", "wipe", "iris", "blinds", "doors", "diag", "split", "drop") and t < TR and i > 0:
                k = t / TR
                prev = self.full_shot(i - 1, shots[i - 1][1] + t).convert("RGB")
                cur = self.full_shot(i, t).convert("RGB")
                if tr == "whip":
                    off = int(ease(k) * self.W)
                    canvas = Image.new("RGB", (self.W, self.H))
                    canvas.paste(prev, (-off, 0))
                    canvas.paste(cur, (self.W - off, 0))
                    fr = self.hblur(canvas, math.sin(math.pi * k))
                elif tr == "slide":
                    off = int(ease(k) * self.H)
                    fr = Image.new("RGB", (self.W, self.H))
                    fr.paste(prev, (0, -off))
                    fr.paste(cur, (0, self.H - off))
                elif tr == "fade":
                    fr = Image.blend(prev, cur, ease(k))
                elif tr == "zoom":  # zoom-through: prev pushes in, cur settles from 1.2x
                    e = ease(k)
                    def zc(im, z):
                        w, h = self.W / z, self.H / z
                        x0, y0 = (self.W - w) / 2, (self.H - h) / 2
                        return im.resize((self.W, self.H), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h))
                    rp = self.shot_frame(i - 1, shots[i - 1][1] + t).convert("RGB")  # undecorated: no ghost logo
                    rc = self.shot_frame(i, t).convert("RGB")
                    fr = Image.blend(zc(rp, 1 + 0.25 * e), zc(rc, 1.2 - 0.2 * e), e)
                    fr = self.decorate(fr.convert("RGBA"), i, t).convert("RGB")
                elif tr == "split":  # previous shot splits horizontally, halves slide up and down
                    e = ease(k)
                    off = int(e * self.H / 2)
                    fr = cur.copy()
                    top = prev.crop((0, 0, self.W, self.H // 2))
                    bot = prev.crop((0, self.H // 2, self.W, self.H))
                    fr.paste(top, (0, -off))
                    fr.paste(bot, (0, self.H // 2 + off))
                    if 0 < off < self.H // 2:
                        dd = ImageDraw.Draw(fr)
                        bw = max(4, int(6 * self.W / 1080))
                        dd.rectangle([0, self.H // 2 - off - bw, self.W, self.H // 2 - off], fill=GOLD)
                        dd.rectangle([0, self.H // 2 + off, self.W, self.H // 2 + off + bw], fill=GOLD)
                elif tr == "drop":  # next shot drops in from the top with a small bounce
                    e = k
                    yy = (1 - e) ** 2 * -self.H + (math.sin(e * math.pi) * 0.04 * self.H if e > 0.7 else 0)
                    fr = prev.copy()
                    fr.paste(cur, (0, int(min(yy, 0) if e < 0.7 else -abs(yy) * 0.3)))
                elif tr == "doors":  # next shot opens like two doors from the centre
                    e = ease(k)
                    half = int(e * self.W / 2)
                    fr = prev.copy()
                    if half > 0:
                        fr.paste(cur.crop((self.W // 2 - half, 0, self.W // 2 + half, self.H)), (self.W // 2 - half, 0))
                        dd = ImageDraw.Draw(fr)
                        bw = max(4, int(8 * self.W / 1080))
                        for xx_ in (self.W // 2 - half, self.W // 2 + half):
                            dd.rectangle([xx_ - bw // 2, 0, xx_ + bw // 2, self.H], fill=GOLD)
                elif tr == "diag":  # diagonal reveal from bottom-left with a gold edge
                    e = ease(k)
                    t_ = e * (self.W + self.H)
                    m = Image.new("L", (self.W, self.H), 0)
                    dm = ImageDraw.Draw(m)
                    dm.polygon([(0, self.H), (0, self.H - t_), (t_, self.H)], fill=255)
                    fr = Image.composite(cur, prev, m)
                    if 0.01 < e < 0.99:
                        ImageDraw.Draw(fr).line([(0, self.H - t_), (t_, self.H)], fill=GOLD, width=max(5, int(10 * self.W / 1080)))
                elif tr == "iris":  # circle opens from the centre with a thin gold ring
                    e = ease(k)
                    R = e * math.hypot(self.W, self.H) / 2
                    m = Image.new("L", (self.W, self.H), 0)
                    dm = ImageDraw.Draw(m)
                    dm.ellipse([self.W / 2 - R, self.H / 2 - R, self.W / 2 + R, self.H / 2 + R], fill=255)
                    fr = Image.composite(cur, prev, m)
                    if 0.02 < e < 0.98:
                        rw = max(4, int(8 * self.W / 1080))
                        ImageDraw.Draw(fr).ellipse([self.W / 2 - R, self.H / 2 - R, self.W / 2 + R, self.H / 2 + R], outline=GOLD, width=rw)
                elif tr == "blinds":  # 8 vertical slats turn over to the next shot
                    e = ease(k)
                    n_ = 8
                    sw = self.W / n_
                    m = Image.new("L", (self.W, self.H), 0)
                    dm = ImageDraw.Draw(m)
                    for j in range(n_):
                        lag = j / n_ * 0.4
                        ej = min(max((e - lag) / 0.6, 0), 1)
                        dm.rectangle([j * sw, 0, j * sw + sw * ej, self.H], fill=255)
                    fr = Image.composite(cur, prev, m)
                elif tr == "wipe":  # left-to-right reveal with a gold edge
                    xw = int(ease(k) * self.W)
                    fr = prev.copy()
                    if xw > 0:
                        fr.paste(cur.crop((0, 0, xw, self.H)), (0, 0))
                    dd = ImageDraw.Draw(fr)
                    bw = max(6, int(12 * self.W / 1080))
                    dd.rectangle([xw - bw // 2, 0, xw + bw // 2, self.H], fill=GOLD)
                else:
                    fr = flash(prev, cur, k)
            else:
                fr = self.full_shot(i, t).convert("RGB")
            yield fr

    def preview(self):
        """Hook, a labelled shot and the end card, side by side."""
        lab = next((i for i, s in enumerate(self.shots) if s[3]), 1)
        return [self.full_shot(0, 0.5).convert("RGB"),
                self.full_shot(lab, self.shots[lab][1] * 0.7).convert("RGB"),
                self.end_frame(2.0).convert("RGB")]

    def audio_input(self, out_dir):
        """Original synthesised soundtrack when the listing asks for music, else silence."""
        style = LISTING.get("music")
        if isinstance(style, str) and style.startswith("pro:"):  # music_pro_songs.py, e.g. "pro:07"
            import music_pro_songs
            key = style.split(":", 1)[1].zfill(2)
            mp3 = out_dir / f"soundtrack-pro{key}.mp3"
            if not mp3.exists():
                music_pro_songs.KEYS[key](mp3, sum(s[1] for s in self.shots) + END_DUR)
            return ["-i", str(mp3)]
        if isinstance(style, str):  # one of the approved styles in music_styles.py, e.g. "lofi"
            import music_styles
            music_styles.DUR = sum(s[1] for s in self.shots) + END_DUR
            fn = dict(music_styles.STYLE_KEYS)[style]
            mp3 = out_dir / f"soundtrack-{style}.mp3"
            if not mp3.exists():
                fn(mp3)
            return ["-i", str(mp3)]
        if style:
            from audio import soundtrack
            wav = soundtrack(self.shots, TR, END_DUR, out_dir / "soundtrack.wav")
            return ["-i", str(wav)]
        return ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]

    def render(self, out_dir):
        out = out_dir / f"{LISTING['slug']}-{self.tag}.mp4"
        cmd = ["ffmpeg", "-y", "-loglevel", "error",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{self.W}x{self.H}", "-r", str(FPS), "-i", "-",
               *self.audio_input(out_dir),
               "-shortest", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
               "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "128k",
               "-movflags", "+faststart", str(out)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        cover = None
        for n, fr in enumerate(self.frames()):
            if n == 0:
                cover = fr
            proc.stdin.write(fr.tobytes())
        proc.stdin.close()
        proc.wait()
        if self.hook_style in ("checklist", "beats", "chat"):  # text appears over time: cover shows the full hook
            cover = self.full_shot(0, self.shots[0][1] - 0.4).convert("RGB")
        cover.save(out_dir / f"cover-{self.tag.split('-')[0]}.jpg", quality=93)
        return out


def flash(prev, cur, k):
    white = Image.new("RGB", prev.size, (255, 250, 240))
    if k < 0.5:
        return Image.blend(prev, white, ease(k * 2) * 0.85)
    return Image.blend(cur, white, ease((1 - k) * 2) * 0.85)


FORMATS = [(1080, 1920, "9x16-tiktok-reels-story"), (1080, 1350, "4x5-instagram-post")]

if __name__ == "__main__":
    listing_dir = Path(sys.argv[1]).resolve()
    LISTING = json.loads((listing_dir / "listing.json").read_text())
    PHOTOS = listing_dir / "photos"
    out_dir = listing_dir / "out"
    out_dir.mkdir(exist_ok=True)
    if "--preview" in sys.argv:
        frames = []
        for W, H, tag in FORMATS:
            frames += Renderer(W, H, tag).preview()
        h = 960
        ims = [im.resize((int(im.width * h / im.height), h)) for im in frames]
        sheet = Image.new("RGB", (sum(i.width + 10 for i in ims) - 10, h), "white")
        x = 0
        for im in ims:
            sheet.paste(im, (x, 0))
            x += im.width + 10
        sheet.save(out_dir / "preview.jpg", quality=88)
        print("preview", out_dir / "preview.jpg")
    else:
        for W, H, tag in FORMATS:
            print("rendered", Renderer(W, H, tag).render(out_dir))
