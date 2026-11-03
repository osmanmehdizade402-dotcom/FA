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
HOOK_MIN = 3.0   # hook shot: exactly 3 s (user rule, 2026-11-02)
SHOT_MIN = 2.0   # every labelled shot
END_DUR = 4.8    # end card: price, details, phone
# CTA line above the phone number (user rule; same for every listing until the user changes it)
CTA_TEXT = "Ətraflı məlumat və baxış üçün zəng et"
COMMENT_Q = "Bu ev neçəyə satılır?"
COMMENT_A = "Şərhdə qeyd et"


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


def grade(im):
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
    return [grade(brighten(Image.frombuffer("RGB", (w, h), raw[i * w * h * 3:(i + 1) * w * h * 3])))
            for i in range(n)]


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
        self.shots = [(s[0], (HOOK_MIN if i == 0 else max(s[1], SHOT_MIN))) + tuple(s[2:5])
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
                t = (T("comment_q", COMMENT_Q) + " " if LISTING["hook"]["cta_style"] == "pill" else "") + T("comment_a", COMMENT_A) + " ↓"
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
                    txt = lab.upper()
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
            g[c0:c1, :, 3] = (prof * 165)[:, None].astype(np.uint8)
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
            p0 = int(H * (0.58 if self.tall else 0.55))
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
            if self.hook_style in ("checklist", "beats"):  # rows pop in one by one
                for j, row in enumerate(self.check_rows):
                    a = ease_out((t - 0.35 - 0.35 * j) / 0.25)
                    lay = self.fade(row, a, dy=20 * (1 - a))
                    if lay:
                        im.alpha_composite(lay)
        im.alpha_composite(self.watermark, self.watermark_pos)
        if label:
            a_in = ease_out((t - 0.14) / 0.22)
            a_out = 1 - ease((t - (dur - 0.12)) / 0.12)
            a = min(a_in, a_out)
            lay = self.fade(self.labels[label], a, dy=30 * (1 - a_in))
            if lay:
                im.alpha_composite(lay)
        if i == 0:  # phone box only on the hook shot (user rule)
            im.alpha_composite(self.cta)
        return im

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
            if tr in ("whip", "flash") and t < TR and i > 0:
                k = t / TR
                prev = self.full_shot(i - 1, shots[i - 1][1] + t).convert("RGB")
                cur = self.full_shot(i, t).convert("RGB")
                if tr == "whip":
                    off = int(ease(k) * self.W)
                    canvas = Image.new("RGB", (self.W, self.H))
                    canvas.paste(prev, (-off, 0))
                    canvas.paste(cur, (self.W - off, 0))
                    fr = self.hblur(canvas, math.sin(math.pi * k))
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
        if self.hook_style in ("checklist", "beats"):  # text appears over time: cover shows the full hook
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
