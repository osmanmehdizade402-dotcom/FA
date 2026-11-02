# Montaj — Xəzər Sahil Əmlak ev videoları (BÜTÜN QANUNLAR)

Yeni evlərin montajı **bu qovluqda** aparılır: hər ev `montaj/evler/<ad>/` qovluğunda
(`listing.json` + `photos/` + `out/`). Alətlər `video/` qovluğundadır (render.py, straighten.py,
tiltcheck.py, şriftlər, musiqi) — onları dəyişmə.
İstifadəçi ilə **azərbaycan dilində** danışılır. Aşağıdakı qanunlar istifadəçi tərəfindən təsdiqlənib;
ziddiyyət olanda **ən son verilən qanun** keçərlidir (burada artıq nəzərə alınıb).

---

## A. İş qaydası

1. **Şəkillər 1 və ya 2 hissədə gəlir.** Hər hissədə yalnız qısa təsdiq: "✅ 1-ci hissəni aldım: N şəkil" — heç bir emal etmə.
2. **İcazəsiz başlama.** Bütün şəkillər + evin məlumatları gəlib istifadəçi "hazırla"/"başla" deyəndə işə başla.
3. "Heçnə yazma" deyilsə — yalnız "✅".
4. **İlk saniyə — əvvəl məsləhət.** "Hazırla" deyiləndə render etmədən ƏVVƏL 2–3 giriş (hook) variantını
   **dizayn nümunəsi şəkli + mətn** ilə göndər, eyni zamanda 2–3 "dostuna göndər" mətni təklif et.
   İstifadəçi seçəndən SONRA render et. İstifadəçi bir neçə variant seçərsə, hər birini ayrıca hazırla.
5. **Qanun verəndə yalnız deyiləni et.** Yeni qayda gələndə onu bu fayla yaz və təsdiqlə; köhnə videoları
   özbaşına yenidən render edib göndərmə — yalnız istifadəçi desə.
6. **Fayl altlıqları.** Hər faylı ayrıca göndər, altında hansı tətbiq üçün olduğunu yaz:
   - 9:16 video → "TikTok, Instagram Reels və Instagram Story üçün"
   - 4:5 video → "Instagram post (lent) və Facebook post üçün"
   - cover-9x16.jpg → "TikTok / Reels örtük şəkli"; cover-4x5.jpg → "Instagram post örtük şəkli"
   - paylasim-metni.md → "TikTok / Instagram / Facebook paylaşım mətni və heşteqlər"
7. **Söhbət adı:** yeni söhbətdə `session-counter.txt`-i 1 artır, adı "FA <rəqəm>" qoy (istifadəçi başqa ad deməsə).
8. **Müəllif hüququ xəbərdarlığı:** musiqi, şəkil, mətn, şrift və s.-də risk varsa, işə başlamazdan ƏVVƏL
   xəbər ver (nə risklidir, video silinə/səssizləşə bilər), təhlükəsiz alternativ təklif et, qərarı istifadəçi versin.
   İstifadəçinin göndərdiyi ev şəkilləri onun özünə aiddir.
9. **Partnyor elan mətnləri:** məlumatları götür, mətni HEÇ VAXT birə-bir köçürmə — öz üslubumuzda yenidən yaz.
   Elandakı başqa nömrələr heç yerdə istifadə olunmur.

## B. Videonun məzmunu

10. **Nömrə yox, şərh çağırışı.** Videoda telefon nömrəsi YOXDUR. Giriş kadrında və son kadrda:
    **"Bu ev neçəyə satılır? Şərhdə qeyd et"**. Nömrə (`010-310-03-02`) yalnız paylaşım mətnində olur.
11. **Qiymət videoda yazılmır** — istifadəçinin məlumatında olsa belə. "QİYMƏTİ SONDA" yazılmır.
    Qiymət yalnız paylaşım mətnində ola bilər (istifadəçi əks deməsə).
11a. **İSTİSNA — ukrayna dilində videolar (Facebook qrupları / Telegram üçün):** qiymət videoda
    (son kadrda) MÜTLƏQ yazılır, məs. "655 000 ₼", və paylaşım mətnində də olur. Qiymət məlum deyilsə,
    istifadəçidən soruş. Nömrə formatı: "+994 10 310 03 02 +WP" (videoda və mətndə).
12. **"Dostuna göndər" çağırışı** hər videoda (son kadrda): marağı çəkən, "hə, dərhal göndərirəm" dedirdən,
    evə uyğun, hər evdə fərqli mətn (məs. "Bu videonu 'bir gün belə evimiz olacaq' dediyin adama göndər!").
    Video içində emoji işlətmə (şrift göstərmir) — emoji yalnız paylaşım mətnində.
13. **Hər şəklin üstündə nə olduğu yazılır:** Hovuz, Həyət, Fasad, Mətbəx, Qonaq otağı, Yataq otağı, Sanuzel,
    Qarderob, Dəhliz, Giriş holu, Yay-qış mətbəxi və s. (giriş kadrından başqa).
    **Zal** şəklində yemək masası olsa belə yazı **"Qonaq otağı"** — heç vaxt "Yemək zonası".
14. **Son kadr:** yaşıl fon, loqo, "SATILIR", evin məlumatları 3 sətirdə, "Bu ev neçəyə satılır?",
    qızılı "Şərhdə qeyd et ↓" düyməsi, "dostuna göndər" mətni; sonda girişə yumşaq keçid (loop).

## C. Dizayn

15. **Hər evin dizaynı fərqli.** Giriş kompozisiyası, yazıların yeri/üslubu, kadr yazısı stili (`label_style`),
    keçidlər, ritm hər evdə dəyişir. Hazır giriş üslubları: `classic`, `pov`, `guess`, `stat`, `checklist`, `cinema`, `beats`, `ribbon`, `split` (render.py `build_hook_v2`) —
    lazım olsa yenisini əlavə et.
16. **Brend sabitdir:** loqo sol (və ya sağ) yuxarıda, nümunədən 20% böyük; "Xəzər Sahil" ağ, "Əmlak" və
    "REAL ESTATE" qızılı. Brend adı **Xəzər Sahil Əmlak**. Rənglər: yaşıl `#163E3A`, qızılı `#C2A365`,
    krem `#F1EFE8`, tünd yaşıl `#0F2E2A`. Şriftlər: Playfair Display Bold, Montserrat 600/700.

## D. Şəkil emalı (hər montajda, xatırlatma lazım deyil)

17. **Əyrilik düzəldilir** (`video/straighten.py`, perspektiv düzəltmə). Render-dən ƏVVƏL yoxla:
    `python3 ../video/tiltcheck.py evler/<ad> yoxlama.jpg` — əyri qalan kadr varsa düzəlt və ya başqa şəkil seç.
    Göndərəndə hansı şəkillərin düzəldildiyini qısa yaz.
18. **İşıqlandırma** — qaranlıq tonlar avtomatik işıqlandırılır (`brighten`).
19. **Rəng tonu** — canlı, rəngli, kino effekti (`grade`): nümunə `video/reference/reng-tonu-numune.mp4`.
    Sıra: düzəltmə → işıqlandırma → rəng tonu.

## E. Uzunluq və temp

20. **Video maksimum 25–30 saniyə.** Sığmırsa ən zəif/təkrar şəkilləri çıxar (yataq otaqları və əsas otaqlar
    mümkün qədər qalsın); çıxarılanları istifadəçiyə yaz. İstifadəçi konkret şəkli çıxar desə — çıxar.
21. **Temp yavaş:** giriş (başlıq) kadrı **dəqiq 3 san** (QANUN, render.py `HOOK_MIN`), hər yazılı kadr ≥2.0 san, son kadr 4.8 san. Kadrları sürətləndirmə.
22. Şəkil ardıcıllığı: fasad → həyət/hovuz → hol → mətbəx → qonaq otağı → yataq otaqları → qarderob → sanuzellər.

## F. Musiqi

23. İstifadəçi nömrə deyəndə: `"music": "pro:NN"` (1–20, `video/music_pro_songs.py`); köhnə üslublar:
    `"lofi"`, `"jazz"`, `"spa"`, `"cinematic"`, `"trend"` və s. Nömrə deyilməyibsə — musiqisiz.
    Hamısı orijinaldır (müəllif hüququ riski yoxdur).

## G. Formatlar və çıxış

24. Hər ev üçün: 9:16 (1080×1920) və 4:5 (1080×1350) video, 2 örtük şəkli, paylaşım mətni (`out/paylasim-metni.md`).
25. Hər işdən sonra commit + push (`claude/xezer-sahil-logo` budağı və `main`).

---

## Necə işləmək

```bash
cd montaj
mkdir -p evler/<ad>/photos            # şəkilləri bura kopyala: photos/<ad>.jpg
# evler/<ad>/listing.json yaz (nümunə: evler/_numune/listing.json)
python3 ../video/tiltcheck.py evler/<ad> yoxlama.jpg   # əyrilik yoxlaması
python3 ../video/render.py evler/<ad> --preview        # önizləmə -> out/preview.jpg
python3 ../video/render.py evler/<ad>                  # 9:16 + 4:5 + örtüklər -> out/
```

`listing.json` əsas sahələri: `slug`, `comment_cta: true`, `price: null`, `phone`, `details` (3 sətir),
`share` (dostuna göndər mətni), `label_style` (`chip` və ya yoxdur), `music`, `hook` (`style`: classic/pov/guess,
`lines`, `kicker`, `sub`, `cta_style`: pill/answer), `shots` — `[şəkil, saniyə, hərəkət, yazı, keçid]`.
