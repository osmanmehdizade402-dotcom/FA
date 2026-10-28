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

ROOT = Path(__file__).resolve().parent
FONTS = ROOT / "fonts"
LOGO = ROOT.parent / "logo" / "xezer-sahil-emlak-horizontal-transparent.png"
FPS = 30
TR = 0.24  # transition length, seconds
END_DUR = 3.4
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


def load_photo(key):
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = PHOTOS / f"{key}{ext}"
        if p.exists():
            return brighten(Image.open(p).convert("RGB"))
    raise FileNotFoundError(PHOTOS / key)


class Renderer:
    def __init__(self, W, H, tag):
        self.W, self.H, self.tag = W, H, tag
        self.tall = H / W > 1.5
        self.u = H / 1920  # vertical layout unit
        self.fs = 1.0 if self.tall else 0.86  # font scale
        self.shots = [tuple(s[:5]) for s in LISTING["shots"]]
        self.focus = [s[5] if len(s) > 5 else None for s in LISTING["shots"]]
        self.photos = {s[0]: load_photo(s[0]) for s in self.shots}
        self.build_overlays()

    # ---------- camera ----------
    def kb(self, key, motion, p, punch=0.0, focus=None):
        im = self.photos[key]
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
        for text, f, fill, cy in [(LISTING["cta"], f1, GOLD_SOFT, y0 + bh * 0.25),
                                  (LISTING["phone"], f2, WHITE, y0 + bh * 0.64)]:
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

        # shot labels
        f_lab = font("Montserrat700.ttf", 62 * fs)
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

        items.append((self.text_layer([centered("SATILIR", font("Montserrat700.ttf", 40 * fs), GOLD, y, 14 * fs)], False), 0.15))
        y += 70 * fs
        if not LISTING.get("price"):  # no price given: invite a call instead
            fq = font("Playfair700.ttf", 92 * fs)
            items.append((self.text_layer([centered("Qiymət üçün zəng edin", fq, GOLD, y + 40 * fs)], False), 0.3))
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
        items.append((self.text_layer([centered("Zəng et  •  WhatsApp  •  DM yaz", font("Montserrat600.ttf", 38 * fs), CREAM, y)], False), 1.0))
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
            im.alpha_composite(self.grad_hook)
            im.alpha_composite(self.hook)
            # pill pulses gently
            a = 0.75 + 0.25 * math.sin(t * 2 * math.pi * 1.5)
            im.alpha_composite(self.fade(self.hook_pill, a))
        im.alpha_composite(self.watermark, self.watermark_pos)
        if label:
            a_in = ease_out((t - 0.14) / 0.22)
            a_out = 1 - ease((t - (dur - 0.12)) / 0.12)
            a = min(a_in, a_out)
            lay = self.fade(self.labels[label], a, dy=30 * (1 - a_in))
            if lay:
                im.alpha_composite(lay)
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

    def render(self, out_dir):
        out = out_dir / f"{LISTING['slug']}-{self.tag}.mp4"
        cmd = ["ffmpeg", "-y", "-loglevel", "error",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{self.W}x{self.H}", "-r", str(FPS), "-i", "-",
               "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
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
