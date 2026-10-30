# Xəzər Sahil Əmlak — ev elanı videoları

Bu repo Xəzər Sahil Əmlak üçün satılan evlərin TikTok / Instagram videolarını hazırlayır.
İstifadəçi ilə **azərbaycan dilində** danışılır.

## İş qaydaları (QANUN — istifadəçi təsdiqləyib)

1. **Şəkillər 1 və ya 2 hissədə göndərilir.** Hər hissə gələndə yalnız qısa təsdiq yaz
   ("✅ 1-ci hissəni aldım: N şəkil") və gözlə. Heç bir emal etmə.
2. **İcazəsiz başlama.** Bütün şəkillər gəldikdən sonra istifadəçidən icazə al
   (və ya istifadəçi özü "başla" desin). Yalnız bundan sonra render et.
3. İstifadəçi "heçnə yazma" desə, yalnız "✅" ilə cavab ver.
4. **"Bu məlumatlarıdır, hazırla" = tam iş əmri.** İstifadəçi şəkillər + evin məlumatlarını verib
   "hazırla" deyəndə (bütün hissələr gəlibsə) əlavə detal soruşmadan bütün işi bu şablonla gör:
   - **Giriş (başlıq) kadrı:** ən yaxşı fasad/həyət şəkli + evin məlumatları (başlıq, yer • sot • otaq,
     "QİYMƏTİ SONDA ↓").
   - **Qalan HƏR şəklin üstündə nə olduğu yazılır:** "Yataq otağı", "Qonaq otağı", "Mətbəx",
     "Sanuzel", "Qaraj", "Hovuz", "Həyət", "Qarderob", "Dəhliz", "Giriş holu" və s.
     (`listing.json`-da heç bir kadrın yazısı `null` qalmasın — yalnız giriş kadrının).
   - **Zal (QANUN):** qonaq otağı/zal şəklində yemək masası olsa belə yazı "Qonaq otağı" olur —
     heç vaxt "Yemək zonası"/"Yemək otağı" yazma.
   - Nömrə: istifadəçinin göndərdiyi elan mətnində başqa nömrə olsa belə HƏMİŞƏ öz nömrəmiz
     (`010-310-03-02`) — istifadəçi açıq desə dəyiş.
   - **Ən sonda HƏMİŞƏ son kadr şablonu:** `video/reference/approved-end-card.png` kimi — yaşıl fon,
     loqo, "SATILIR", qiymət ₼, evin bütün məlumatları 3 sətirdə, qızılı düymədə nömrə
     (`010 310 03 02`, boşluqla), "Zəng et • WhatsApp • DM yaz".
   - Hər iki formatı (9:16 və 4:5) render et, örtük şəkilləri + paylaşım mətni/heşteqlərlə göndər.
   - Qiymət verilməyibsə gözləmə: `"price": null` qoy (son kadrda "Qiymət üçün zəng edin",
     girişdə "ƏTRAFLI SONDA ↓"), render et və qiyməti verərsə yenidən render edəcəyini de.
   - Şəkil az olanda bir şəkildən bir neçə kadr çıxar: kadrın 6-cı elementi `[fx, fy, zoom]`
     (məs. `[0.30, 0.58, 1.45]`) şəklin həmin hissəsinə yaxınlaşır — hər kadra öz yazısı.
   - Nömrə qutusunun üst yazısı HƏMİŞƏ "Ətraflı məlumat və baxış üçün zəng et" (render.py
     `CTA_TEXT`) — istifadəçi "dəyişdir" deyənə qədər bütün evlərdə eyni.

5. **Hər faylın altında hansı tətbiq üçün olduğu yazılır.** Video/şəkil göndərəndə hər faylı
   ayrıca göndər və altlığında (caption) yaz, məs.:
   - 9:16 video → "TikTok, Instagram Reels və Instagram Story üçün"
   - 4:5 video → "Instagram post (lent) və Facebook post üçün"
   - cover-9x16.jpg → "TikTok / Reels örtük şəkli"; cover-4x5.jpg → "Instagram post örtük şəkli"
   - paylasim-metni.md → "TikTok / Instagram / Facebook paylaşım mətni və heşteqlər"
6. **Qanun verəndə yalnız deyiləni et.** İstifadəçi yeni qayda verəndə qaydanı qeyd et və təsdiqlə —
   köhnə evləri/prototipləri yenidən render edib təkrar göndərmə. Bunu yalnız istifadəçi özü
   desə et.

7. **Söhbət adları sıra nömrəli (QANUN):** hər YENİ söhbətin əvvəlində `session-counter.txt`-dəki
   rəqəmi 1 artır, söhbətin adını `set_session_title` ilə "FA <rəqəm>" qoy (məs. "FA 2"),
   faylı commit + push et. Söhbət adı heç vaxt sadəcə "FA" olmasın. "FA 1" = ilk söhbət.

8. **Müəllif hüququ xəbərdarlığı (QANUN — bütün işlərdə, istifadəçi xatırlatmasa belə):**
   hər hansı layihədə (video, şəkil, musiqi/səs, mətn, şrift, loqo, başqasının elanı və s.)
   müəllif hüququnun pozulması riski varsa, işə başlamazdan ƏVVƏL istifadəçiyə açıq xəbərdarlıq et:
   nə risklidir, kimin hüququdur, və YouTube/Instagram/TikTok/Facebook-da paylaşılarsa videonun
   silinə, səssizləşdirilə və ya hesabın cərimələnə biləcəyini de. Təhlükəsiz alternativ təklif et
   və qərarı istifadəçi versin — qərar gəlməmiş riskli hissəni etmə.

## Brend şablonu (DƏYİŞMİR — hər ev üçün eyni)

Təsdiqlənmiş nümunələr: `video/reference/approved-hook-4x5.jpg` (giriş kadrı) və
`video/reference/approved-end-card.png` (son kadr). Nümunə ev: `video/listings/merdekan-villa/`.
Bütün dizayn `video/render.py`-də sabitdir — yeni ev üçün onu dəyişmə, yalnız `listing.json` yaz.

- **Loqo (sol yuxarı, bütün kadrlarda):** yaşıl ikon + "Xəzər Sahil" (ağ) "Əmlak" (qızılı, konturs) +
  "REAL ESTATE" (qızılı, DejaVu Sans Bold) — qızılı hissələr digər qızılı elementlərlə eyni rəngdə. Mənbə: `logo/xezer-sahil-emlak-horizontal-transparent.png`.
  Brend adı **Xəzər Sahil Əmlak** (Xəzər Sahil Ev yox).
  Ölçü: nümunədən 20% böyük (istifadəçi "1 düyüm böyüt" dedi) — render.py-də `* 1.2`.
- **Rənglər:** yaşıl `#163E3A`, qızılı `#C2A365`, krem `#F1EFE8`, CTA qutusu `#0F2E2A`.
- **Şriftlər** (`video/fonts/`): başlıq Playfair Display Bold, mətn Montserrat 600/700,
  CTA qutusu DejaVu Sans / DejaVu Sans Bold. Ölçülər render.py-dəki kimi qalır.
- **Giriş kadrı:** ən yaxşı fasad şəkli + 2 sətirli başlıq (1-ci krem, 2-ci qızılı) +
  alt sətir (yer • sot • otaq) + qızılı "QİYMƏTİ SONDA ↓" düyməsi.
- **Nömrə qutusu (QANUN — YALNIZ giriş/başlıq kadrında):** tünd yaşıl, qızılı çərçivə; üst sətir
  "Ətraflı məlumat və baxış üçün zəng et", alt sətir böyük ağ nömrə (`010-310-03-02`, defislə).
  Sonrakı kadrlarda nömrə qutusu YOXDUR — orada yalnız loqo və kadrın yazısı (Hovuz, Mətbəx...) olur.
  Nömrə yenə son kadrda görünür.
- **Şəkillər düzəldilir (QANUN):** azacıq əyri şəkillər avtomatik düzəldilir (`video/straighten.py`:
  şaquli xətlərə — divar, qapı, sütun — görə 0.25°–4° əyilmə düzəldilir, kənarlar kəsilir).
  OpenCV lazımdır: `pip install opencv-python-headless`.
- **Şəkillər işıqlandırılır (QANUN):** qaranlıq tonlar hər şəklin öz parlaqlığına görə avtomatik
  işıqlandırılır (render.py `brighten`) — əvvəl düzəltmə, sonra işıqlandırma.
- **Sonluq:** yaşıl fon, loqo, "SATILIR", qiymət + ₼, 3 sətir xüsusiyyət, qızılı telefon düyməsi;
  sonda girişə keçid (loop).
- **Temp (QANUN):** yavaş — hər yazı növbəti keçidə qədər rahat oxunmalıdır. render.py-də minimum:
  giriş kadrı 3.2 san, hər yazılı kadr 2.0 san, son kadr 4.8 san, keçid 0.3 san. Bunları azaltma.
  Video çox uzanırsa (>~35 san), kadrları sürətləndirmə — ən zəif/təkrar şəkilləri çıxar.
- **Formatlar:** 9:16 (TikTok/Reels/Story) və 4:5 (Instagram post), 30fps, səssiz audio
  trek (trend səsi istifadəçi tətbiqdə əlavə edir).

## Hər ev üçün dəyişənlər (`video/listings/<slug>/listing.json`)

Başlıq (məs. "Hovuzlu / villa"), alt sətir, qiymət, 3 xüsusiyyət sətri,
telefon (default `010-310-03-02` — istifadəçi başqa nömrə verməsə dəyişmə), kadr siyahısı
(şəkil, saniyə, hərəkət, yazı, keçid). Şəkilləri `photos/<ad>.jpg` kimi kopyala.
Çatışmayan məlumatı (yer, sot, otaq, hamam, qiymət, xüsusiyyətlər) istifadəçidən soruş.

## Necə render etmək

```bash
cd video
python3 render.py listings/<slug> --preview   # əvvəl önizləmə (out/preview.jpg) — yoxla
python3 render.py listings/<slug>             # 9:16 + 4:5 mp4 və örtük şəkilləri -> out/
```

Yazıların fasadın açıq hissəsinə düşmədiyini, CTA qutusu ilə üst-üstə gəlmədiyini önizləmədə yoxla.
Nəticəni istifadəçiyə göndər + paylaşım mətni/heşteqlər yaz (bax `video/out/paylasim-metni.md` nümunəsi).
