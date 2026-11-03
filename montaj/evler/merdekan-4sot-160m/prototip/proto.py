import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
sys.path.insert(0, "/home/user/FA/video")
from render import font, brighten, GOLD, GREEN, CREAM, WHITE
from straighten import straighten
P = Path("/home/user/FA/montaj/evler/merdekan-4sot-160m/photos")
OUT = Path("/home/user/FA/montaj/evler/merdekan-4sot-160m/prototip")
W, H = 1080, 1920

def photo(k, fx=0.5, fy=0.5, z=1.0):
    im = straighten(Image.open(P / f"{k}.jpg").convert("RGB"))[0]
    im = brighten(im)
    iw, ih = im.size
    ar = W / H
    cw, ch = (ih * ar, ih) if iw / ih > ar else (iw, iw / ar)
    cw, ch = cw / z, ch / z
    x0 = min(max(fx * iw - cw / 2, 0), iw - cw); y0 = min(max(fy * ih - ch / 2, 0), ih - ch)
    return im.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))

def outline_text(d, xy, t, f, fill, stroke=8, anchor="mm"):
    d.text(xy, t, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0))

def grad(im, top=0, bot=0):
    g = np.zeros((H, W, 4), np.uint8)
    if top:
        n = int(H * 0.35); g[:n, :, 3] = (np.linspace(1, 0, n) * top)[:, None]
    if bot:
        g0 = int(H * 0.5); g[g0:, :, 3] = np.maximum(g[g0:, :, 3], (np.linspace(0, 1, H - g0) * bot)[:, None])
    im = im.convert("RGBA"); im.alpha_composite(Image.fromarray(g, "RGBA")); return im

# ---------- A: Baku high-performing local style ----------
def local():
    fr = []
    YEL = (255, 214, 0)
    # 1 hook: face-to-camera feel replaced by bold question + spec stickers
    im = grad(photo("facade"), top=170, bot=200); d = ImageDraw.Draw(im)
    outline_text(d, (W/2, 250), "MƏRDƏKANDA", font("Montserrat700.ttf", 78), WHITE)
    outline_text(d, (W/2, 360), "BU QİYMƏTƏ", font("Montserrat700.ttf", 104), YEL)
    outline_text(d, (W/2, 480), "HOVUZLU EV?!", font("Montserrat700.ttf", 104), YEL)
    y = 1250
    for t in ["4 sot", "160 m²", "4 otaq", "Kupça"]:
        f = font("Montserrat700.ttf", 54); tw = d.textlength(t, font=f)
        d.rounded_rectangle([W/2 - tw/2 - 40, y, W/2 + tw/2 + 40, y + 92], radius=20, fill=WHITE)
        d.text((W/2, y + 46), t, font=f, fill=(20, 20, 20), anchor="mm"); y += 112
    fr.append(("1. Hook (0–1 san)", ["Sual + 'şok' sözü, sarı-qara", "TikTok subtitr üslubu", "Rəqəmlər stiker kimi"], im))
    # 2 room with subtitle captions (voice-over style)
    im = grad(photo("living2"), bot=150); d = ImageDraw.Draw(im)
    outline_text(d, (W/2, 1330), "Zal bax beləə genişdir", font("Montserrat700.ttf", 66), WHITE)
    outline_text(d, (W/2, 1420), "üstəlik TAM ƏŞYALI", font("Montserrat700.ttf", 66), YEL)
    d.rounded_rectangle([60, 180, 420, 270], radius=45, fill=(230, 30, 40))
    d.ellipse([92, 211, 120, 239], fill=WHITE)
    d.text((262, 225), "CANLI BAXIŞ", font=font("Montserrat700.ttf", 40), fill=WHITE, anchor="mm")
    fr.append(("2. Ev turu", ["Səsli izah + altyazı (danışıq dili)", "'Canlı baxış' hissi", "Sürətli kəsik, 1–1.5 san"], im))
    # 3 pool lifestyle with 'save' prompt
    im = grad(photo("pool"), bot=170); d = ImageDraw.Draw(im)
    outline_text(d, (W/2, 1330), "Yayda hovuz, qışda", font("Montserrat700.ttf", 66), WHITE)
    outline_text(d, (W/2, 1420), "yay-qış mətbəxi", font("Montserrat700.ttf", 66), YEL)
    outline_text(d, (W/2, 300), "SAXLA, İTİRMƏ", font("Montserrat700.ttf", 60), WHITE, stroke=6)
    fr.append(("3. Ortada tutma", ["'Saxla' çağırışı ortada", "İzləyicini sona qədər saxlayır"], im))
    # 4 end: comment keyword
    im = photo("gazebo").filter(ImageFilter.GaussianBlur(18)); im = ImageEnhance.Brightness(im).enhance(0.45).convert("RGBA"); d = ImageDraw.Draw(im)
    outline_text(d, (W/2, 700), "Qiyməti öyrənmək üçün", font("Montserrat700.ttf", 62), WHITE)
    outline_text(d, (W/2, 800), "şərhə yaz:", font("Montserrat700.ttf", 62), WHITE)
    d.rounded_rectangle([W/2 - 260, 900, W/2 + 260, 1060], radius=30, fill=YEL)
    d.text((W/2, 980), "\"EV\"", font=font("Montserrat700.ttf", 110), fill=(20, 20, 20), anchor="mm")
    outline_text(d, (W/2, 1180), "DM-ə detalları göndərirəm", font("Montserrat600.ttf", 50), WHITE, stroke=5)
    fr.append(("4. Son", ["Bir söz şərh ('EV') -> alqoritm", "DM-ə keçid = real müştəri"], im))
    return fr

# ---------- B: world luxury real-estate film style ----------
def lux():
    fr = []
    def mute(im):
        im = ImageEnhance.Color(im).enhance(0.78); im = ImageEnhance.Contrast(im).enhance(0.92)
        a = np.asarray(im).astype(np.float32); a = a * 0.94 + np.array([10, 8, 4]); return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    fs = font("Playfair700.ttf", 64); ft = font("Montserrat600.ttf", 30)
    def tracked(d, y, t, f, fill, tr=10):
        w = sum(d.textlength(c, font=f) + tr for c in t) - tr; x = W/2 - w/2
        for c in t: d.text((x, y), c, font=f, fill=fill); x += d.textlength(c, font=f) + tr
    # 1 hook: detail first, minimal title
    im = mute(photo("living2", 0.70, 0.30, 1.9)).convert("RGBA"); d = ImageDraw.Draw(im)
    tracked(d, 1500, "MƏRDƏKAN, ABŞERON", ft, CREAM, 12)
    d.text((W/2, 1600), "Tağlar evi", font=fs, fill=CREAM, anchor="mm")
    d.line([(W/2 - 40, 1670), (W/2 + 40, 1670)], fill=CREAM, width=2)
    fr.append(("1. Açılış (0–3 san)", ["Detal kadrı ilə başlayır (çilçıraq)", "Evə ad verilir: 'Tağlar evi'", "Kiçik, seyrək yazı, çox boşluq"], im))
    # 2 architecture with thin frame + chapter number
    im = mute(photo("facade")).convert("RGBA"); d = ImageDraw.Draw(im)
    d.rectangle([40, 40, W - 40, H - 40], outline=CREAM + (200,), width=2)
    tracked(d, 120, "I — MEMARLIQ", ft, CREAM, 10)
    fr.append(("2. Fəsillər", ["Video hissələrə bölünür: I, II, III", "Yalnız kadr, yazı minimum", "Yavaş, sabit kamera (gimbal)"], im))
    # 3 lifestyle moment
    im = mute(photo("gazebo", 0.5, 0.55, 1.15)).convert("RGBA"); d = ImageDraw.Draw(im)
    tracked(d, 120, "III — AXŞAM", ft, CREAM, 10)
    d.text((W/2, 1640), "“Qonaqlar gedəndən sonra", font=font("Playfair700.ttf", 44), fill=CREAM, anchor="mm")
    d.text((W/2, 1700), "ən sevdiyin yer.”", font=font("Playfair700.ttf", 44), fill=CREAM, anchor="mm")
    fr.append(("3. Həyat tərzi", ["Otaq deyil, HİS satılır", "Axşam/qızıl saat işığı", "Bir cümləlik hekayə"], im))
    # 4 end: quiet card
    im = Image.new("RGBA", (W, H), (24, 26, 25, 255)); d = ImageDraw.Draw(im)
    d.text((W/2, 820), "Tağlar evi", font=font("Playfair700.ttf", 92), fill=CREAM, anchor="mm")
    tracked(d, 920, "4 SOT  ·  160 M²  ·  4 OTAQ  ·  HOVUZ", ft, (190, 185, 172), 8)
    d.line([(W/2 - 60, 1010), (W/2 + 60, 1010)], fill=GOLD, width=2)
    tracked(d, 1050, "ŞƏXSİ BAXIŞ ÜÇÜN YAZIN", ft, GOLD, 10)
    tracked(d, 1700, "XƏZƏR SAHİL ƏMLAK", font("Montserrat600.ttf", 26), (150, 146, 136), 12)
    fr.append(("4. Son", ["Sakit, tünd kart", "'Şəxsi baxış' — eksklüzivlik", "Loqo kiçik, ən aşağıda"], im))
    return fr

def sheet(frames, title, sub, name, bg, fg):
    tw, th = 405, 720; pad = 30; cap = 230
    S = Image.new("RGB", (pad + len(frames) * (tw + pad), 170 + th + cap), bg); d = ImageDraw.Draw(S)
    d.text((pad, 30), title, font=font("Playfair700.ttf", 54), fill=fg)
    d.text((pad, 105), sub, font=font("Montserrat600.ttf", 26), fill=fg)
    for i, (h, lines, im) in enumerate(frames):
        x = pad + i * (tw + pad)
        S.paste(im.convert("RGB").resize((tw, th), Image.LANCZOS), (x, 170))
        d.text((x, 170 + th + 18), h, font=font("Montserrat700.ttf", 28), fill=fg)
        for j, l in enumerate(lines):
            d.text((x, 170 + th + 62 + j * 36), "• " + l, font=font("Montserrat600.ttf", 21), fill=fg)
    S.save(OUT / name, quality=92)

sheet(local(), "Prototip A — Bakı: ən çox baxış toplayan yerli üslub",
      "Bir dəfəlik öyrənmə nümunəsi • Sizin şəkillər (Mərdəkan, 4 sot, 160 m²)", "prototip-A-baki.jpg", (245, 245, 240), (20, 20, 20))
sheet(lux(), "Prototip B — Dünya: lüks əmlak filmi üslubu",
      "Bir dəfəlik öyrənmə nümunəsi • Sizin şəkillər (Mərdəkan, 4 sot, 160 m²)", "prototip-B-dunya.jpg", (24, 26, 25), CREAM)
print("ok")
