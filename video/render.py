"""Xəzər Sahil Əmlak — Mərdəkan villa promo video renderer.

Renders 9:16 (TikTok / Reels / Story) and 4:5 (Instagram feed) versions from
the listing photos: Ken Burns motion, beat-length cuts, whip/punch/flash
transitions, branded labels, price end card that loops back into the hook.

Usage: python3 render.py <photo_dir> <font_dir> <logo_png> <out_dir>
"""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

PHOTOS, FONTS, LOGO, OUT = (Path(a) for a in sys.argv[1:5])
FPS = 30
TR = 0.24  # transition length, seconds

GREEN = (22, 62, 58)
GOLD = (194, 163, 101)
CREAM = (241, 239, 232)

# Photo ids (uploaded file prefixes)
P = {
    "facade_pool": "0f2acfc3", "porch_pool": "ddd20c06", "facade_walk": "c3619711",
    "swing": "ad91cfb8", "garage": "b6919016", "pergola": "68fc86cc",
    "summer_view": "0b9c30db", "entrance": "abecb15b", "hall": "6b5289a2",
    "living": "b7083204", "kitchen": "02c6ad07", "dining": "b501b4e7",
    "bed1": "a785a060", "bed3": "5aa21221", "bed2": "3f4cbbda",
    "closet": "0d5e13ac", "bath_tub": "99d2106c", "bath2": "f82ca7ab",
    "corridor": "551f8f00",
}

# (photo, seconds, motion, label, transition-into-this-shot)
SHOTS = [
    ("facade_pool", 2.0, "in_slow", None, None),
    ("facade_walk", 1.0, "in", None, "whip"),
    ("porch_pool", 0.9, "left", "Hovuz", "punch"),
    ("swing", 0.9, "out", None, "whip"),
    ("garage", 1.0, "right", "Qaraj + geniş həyət", "punch"),
    ("pergola", 0.9, "in", None, "whip"),
    ("summer_view", 1.1, "in", "Yay mətbəxi", "punch"),
    ("entrance", 1.2, "up", "Giriş holu", "flash"),
    ("hall", 0.8, "in", None, "punch"),
    ("living", 1.0, "in", "Qonaq otağı", "whip"),
    ("kitchen", 1.0, "out", "Mətbəx", "punch"),
    ("dining", 0.8, "left", None, "whip"),
    ("bed1", 1.0, "in", "5 otaq", "punch"),
    ("bed3", 0.8, "right", None, "whip"),
    ("bed2", 0.7, "in", None, "punch"),
    ("closet", 1.2, "left", "2 qarderob", "whip"),
    ("bath_tub", 1.0, "in", "3 hamam + tualet", "punch"),
    ("bath2", 0.8, "out", None, "whip"),
    ("corridor", 0.9, "in_fast", None, "punch"),
]
END_DUR = 3.4
END_LOOP = 0.4  # final crossfade back into frame 0 for a seamless loop


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), int(size))


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def load_photo(key):
    im = Image.open(PHOTOS / f"{P[key]}-image.jpg").convert("RGB")
    im = ImageEnhance.Color(im).enhance(1.12)
    im = ImageEnhance.Contrast(im).enhance(1.06)
    return im


class Renderer:
    def __init__(self, W, H, tag):
        self.W, self.H, self.tag = W, H, tag
        self.u = H / 1920  # vertical layout unit
        self.fs = 1.0 if H / W > 1.5 else 0.86  # font scale
        self.photos = {k: load_photo(k) for k, *_ in SHOTS}
        self.build_overlays()

    # ---------- camera ----------
    def kb(self, key, motion, p, punch=0.0):
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

    def build_overlays(self):
        W, H, u, fs = self.W, self.H, self.u, self.fs
        mx = int(70 * W / 1080)

        # top gradient so the watermark and hook text stay readable
        g = np.zeros((H, W, 4), np.uint8)
        g0 = int(H * 0.40)
        ramp = np.clip(np.linspace(0, 1.6, H - g0), 0, 1) ** 1.3
        g[g0:, :, 3] = (ramp * 185)[:, None].astype(np.uint8)
        self.grad_hook = Image.fromarray(g, "RGBA")
        g2 = g.copy()
        h2 = int(H * 0.2)
        g2[:, :, 3] = 0
        g2[:h2, :, 3] = np.linspace(90, 0, h2)[:, None].astype(np.uint8)
        self.grad_top = Image.fromarray(g2, "RGBA")

        logo = Image.open(LOGO).convert("RGBA")
        lw = int(430 * W / 1080)
        self.logo_small = logo.resize((lw, int(lw * logo.height / logo.width)), Image.LANCZOS)
        self.logo_pos = (mx, int(150 * u))

        # hook
        f_big = font("Playfair700.ttf", 118 * fs)
        f_sub = font("Montserrat600.ttf", 42 * fs)
        y = int(H * 0.50)
        parts = [("Hovuzlu", f_big, CREAM, mx, y, 0)]
        y += int(132 * fs)
        parts.append(("villa", f_big, GOLD, mx, y, 0))
        y += int(165 * fs)
        parts.append(("Mərdəkan  •  6.5 sot  •  5 otaq", f_sub, CREAM, mx, y, 0))
        self.hook = self.text_layer(parts)
        # "price at the end" pill
        f_pill = font("Montserrat700.ttf", 36 * fs)
        pill_txt = "QİYMƏTİ SONDA  ↓"
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
        ly = int(1180 * u) if H / W > 1.5 else int(H * 0.70)
        for _, _, _, lab, _ in SHOTS:
            if not lab:
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
        bg = self.kb("facade_pool", "in_slow", 0.0).filter(ImageFilter.GaussianBlur(28))
        bg = Image.blend(bg, Image.new("RGB", bg.size, GREEN), 0.80).convert("RGBA")
        self.end_bg = bg

        cx = W / 2
        d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        items = []  # (layer, appear_time)

        def centered(text, f, fill, y, track=0):
            w = sum(d.textlength(c, font=f) + track for c in text) - track
            return (text, f, fill, cx - w / 2, y, track)

        tall = H / W > 1.5
        y = H * (0.17 if tall else 0.08)
        lw = int(W * 0.70)
        lg = logo.resize((lw, int(lw * logo.height / logo.width)), Image.LANCZOS)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lay.alpha_composite(lg, (int(cx - lw / 2), int(y)))
        items.append((lay, 0.0))
        y += lg.height + 60 * fs

        items.append((self.text_layer([centered("SATILIR", font("Montserrat700.ttf", 40 * fs), GOLD, y, 14 * fs)], False), 0.15))
        y += 70 * fs
        # price: Playfair digits + Montserrat manat sign
        fp = font("Playfair700.ttf", 160 * fs)
        fm = font("Montserrat700.ttf", 120 * fs)
        num, cur = "655 000 ", "₼"
        wn, wc = d.textlength(num, font=fp), d.textlength(cur, font=fm)
        x0 = cx - (wn + wc) / 2
        base = y + fp.getmetrics()[0]
        lay = self.text_layer([(num, fp, GOLD, x0, y, 0),
                               (cur, fm, GOLD, x0 + wn, base - fm.getmetrics()[0], 0)], False)
        items.append((lay, 0.3))
        y += 230 * fs

        fd = font("Montserrat600.ttf", 44 * fs)
        for i, line in enumerate(["Mərdəkan  •  6.5 sot  •  Həyət evi",
                                  "5 otaq  •  3 hamam  •  2 qarderob",
                                  "Hovuz  •  Qaraj  •  Yay mətbəxi"]):
            items.append((self.text_layer([centered(line, fd, CREAM, y, 0)], False), 0.5 + 0.1 * i))
            y += 70 * fs
        y += 45 * fs

        # phone pill
        fph = font("Montserrat700.ttf", 64 * fs)
        phone = "010 310 03 02"
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
        key, dur, motion, label, _ = SHOTS[i]
        tr = SHOTS[i][4]
        punch = 0.10 * (1 - ease_out(t / TR)) if tr == "punch" and t < TR else 0.0
        im = self.kb(key, motion, t / dur, punch).convert("RGBA")
        return im

    def decorate(self, im, i, t):
        key, dur, motion, label, _ = SHOTS[i]
        if i == 0:
            im.alpha_composite(self.grad_hook)
            im.alpha_composite(self.hook)
            # pill pulses gently
            a = 0.75 + 0.25 * math.sin(t * 2 * math.pi * 1.5)
            im.alpha_composite(self.fade(self.hook_pill, a))
        else:
            im.alpha_composite(self.grad_top)
        im.alpha_composite(self.logo_small, self.logo_pos)
        if label:
            a_in = ease_out((t - 0.14) / 0.22)
            a_out = 1 - ease((t - (dur - 0.12)) / 0.12)
            a = min(a_in, a_out)
            lay = self.fade(self.labels[label], a, dy=30 * (1 - a_in))
            if lay:
                im.alpha_composite(lay)
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
        starts, acc = [], 0.0
        for s in SHOTS:
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
                    k = t / TR
                    prev = self.full_shot(len(SHOTS) - 1, SHOTS[-1][1] + t).convert("RGB")
                    cur = self.end_frame(t).convert("RGB")
                    fr = flash(prev, cur, k)
                elif t > END_DUR - END_LOOP:
                    k = ease((t - (END_DUR - END_LOOP)) / END_LOOP)
                    fr = Image.blend(self.end_frame(t).convert("RGB"), first, k)
                else:
                    fr = self.end_frame(t).convert("RGB")
                yield fr
                continue
            i = max(j for j, s in enumerate(starts) if s <= T + 1e-9)
            t = T - starts[i]
            tr = SHOTS[i][4]
            if tr in ("whip", "flash") and t < TR and i > 0:
                k = t / TR
                prev = self.full_shot(i - 1, SHOTS[i - 1][1] + t).convert("RGB")
                cur = self.full_shot(i, t).convert("RGB")
                if tr == "whip":
                    e = ease(k)
                    off = int(e * self.W)
                    canvas = Image.new("RGB", (self.W, self.H))
                    canvas.paste(prev, (-off, 0))
                    canvas.paste(cur, (self.W - off, 0))
                    fr = self.hblur(canvas, math.sin(math.pi * k))
                else:
                    fr = flash(prev, cur, k)
            else:
                fr = self.full_shot(i, t).convert("RGB")
            yield fr

    def render(self):
        OUT.mkdir(parents=True, exist_ok=True)
        out = OUT / f"xezer-sahil-merdekan-{self.tag}.mp4"
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
        cover.save(OUT / f"cover-{self.tag}.jpg", quality=93)
        return out


def flash(prev, cur, k):
    white = Image.new("RGB", prev.size, (255, 250, 240))
    if k < 0.5:
        return Image.blend(prev, white, ease(k * 2) * 0.85)
    return Image.blend(cur, white, ease((1 - k) * 2) * 0.85)


if __name__ == "__main__":
    for W, H, tag in [(1080, 1920, "9x16-tiktok-reels-story"), (1080, 1350, "4x5-instagram-post")]:
        print("rendered", Renderer(W, H, tag).render())
