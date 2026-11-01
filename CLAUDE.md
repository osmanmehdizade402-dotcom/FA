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
     loqo, "SATILIR", evin bütün məlumatları 3 sətirdə, qızılı düymədə nömrə
     (`010 310 03 02`, boşluqla), "Zəng et • WhatsApp • DM yaz". **Qiymət YAZILMIR** (bax 10-cu qanun).
   - Hər iki formatı (9:16 və 4:5) render et, örtük şəkilləri + paylaşım mətni/heşteqlərlə göndər.
   - Qiymət videoya heç vaxt yazılmır (10-cu qanun) — qiymət verilməsə də gözləmə, render et.
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

9. **Partnyor elanlarının mətni (QANUN):** istifadəçi birgə işlədiyi agentliklərin elan mətnini
   göndərəndə məlumatları (yer, sot, m², otaqlar, xüsusiyyətlər, qiymət) götür, amma mətni
   HEÇ VAXT birə-bir köçürmə — öz üslubumuzda, fərqli quruluş və ifadələrlə yenidən yaz ki,
   paylaşım təkrar görünməsin (cəlbedici giriş cümləsi, qruplaşdırılmış xüsusiyyətlər, şərhə çağırış).
   Şəkillər istifadəçinin özünə aiddir — onlar üçün müəllif hüququ xəbərdarlığı lazım deyil.

10. **Yeni video qanunları (2026-11-01, istifadəçi təsdiqləyib — köhnə qaydalarla ziddiyyətdə BUNLAR keçərlidir):**
   - **Hər evin dizaynı fərqli olur.** Heç bir ev videosu əvvəlkilərə bənzəməməlidir: giriş kadrının
     kompozisiyası, yazıların yeri/düzülüşü, keçidlər, hərəkət, ilk saniyənin fikri hər evdə yenidir.
     Dəyişməyən yalnız brend kimliyidir: loqo, rənglər, şriftlər, nömrə.
   - **İlk saniyədə maraq (hook) — əvvəl məsləhət, sonra tətbiq.** Hər ev üçün ilk saniyədə maraq
     yaradan fikir tap (sual, sürpriz, müqayisə, hərəkət). Render etməzdən ƏVVƏL fikri istifadəçiyə de,
     nümunə ver (önizləmə şəkli), məsləhətləş — təsdiqdən SONRA tətbiq et.
   - **"Dostuna göndər" sətri.** Hər videoda oxuyanın marağını çəkən, "hə, dərhal göndərirəm" dedirdən
     paylaşım çağırışı olur (məs. konkret adama yönəlmiş: "Hovuz arzulayan dostuna göndər"). Hər evə
     öz mətni — təkrarlanmır; ilk dəfə nümunələri istifadəçi ilə razılaşdır.
   - **Nömrə qutusu → şərh çağırışı.** Giriş kadrındakı nömrə qutusunun yerinə
     "Bu ev neçəyə satılır? Şərhdə qeyd et" yazılır (eyni tünd yaşıl qutu, qızılı çərçivə).
     Nömrə son kadrda qalır.
   - **Qiymət yazılmır.** İstifadəçinin göndərdiyi məlumatda qiymət olsa belə videoda (giriş, son kadr)
     qiymət YOXDUR. "QİYMƏTİ SONDA ↓" də yazılmır.
   - **Uzunluq maksimum 25–30 saniyə.** Bütün video (giriş + kadrlar + son kadr) 30 saniyəni keçmir.
     Sığmırsa ən zəif şəkilləri çıxar (bənzər, bulanıq, qaranlıq, az məlumat verən) və göndərəndə hansıları
     çıxardığını yaz. Bu qanun "bütün şəkillər istifadə olunur" qaydasını əvəz edir.

## Brend şablonu (brend kimliyi dəyişmir; hər evin dizaynı fərqli — 10-cu qanun)

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
  alt sətir (yer • sot • otaq) + ilk saniyənin maraq elementi (10-cu qanun; "QİYMƏTİ SONDA" yox).
- **Başlıq təkrarlanmır (QANUN):** hər yeni evin giriş başlığı (`hook.title`, 2 sətir) əvvəlki
  BÜTÜN evlərin başlıqlarından fərqli olmalıdır — "Hovuzlu villa", "Klassik villa", "Modern villa",
  "Premium villa", "Lüks villa", "Hovuzlu bağ evi" artıq işlənib, bir daha yazılmır. Başlığı evin əsl
  üstünlüyündən seç (məs. "Panoramik / villa", "Ailəvi / bağ evi", "Dəniz yaxını / villa", "Yeni tikili /
  malikanə", "Yaşıl həyətli / ev"). Yazmazdan əvvəl `listings/*/listing.json`-dakı başlıqları yoxla;
  render.py təkrar başlıqda xəbərdarlıq verir — xəbərdarlıq çıxsa başlığı dəyiş.
- **Qutu (QANUN — YALNIZ giriş/başlıq kadrında):** tünd yaşıl, qızılı çərçivə; içində nömrə YOX,
  "Bu ev neçəyə satılır? Şərhdə qeyd et" (10-cu qanun). Əvvəlki variant (köhnə videolar): üst sətir
  "Ətraflı məlumat və baxış üçün zəng et", alt sətir nömrə.
  Sonrakı kadrlarda nömrə qutusu YOXDUR — orada yalnız loqo və kadrın yazısı (Hovuz, Mətbəx...) olur.
  Nömrə yenə son kadrda görünür.
- **Şəkillər düzəldilir (QANUN — HƏR montajda, istifadəçi xatırlatmasa belə):** bütün əyri şəkillər
  (yana əyilmə + geniş bucaqlı kameranın divarları yatırması) `video/straighten.py` ilə perspektiv
  düzəltməsindən keçir — divar, qapı, pərdə, sütun düz dayanmalıdır. Render etməzdən ƏVVƏL hər evdə
  yoxla: `cd video && python3 tiltcheck.py listings/<slug> out.jpg` — əvvəl/sonra şəkillərinə qırmızı
  şaquli xətlərlə bax; əyri qalan kadr varsa düzəlt və ya başqa şəkil seç. Göndərəndə hansı şəkillərin
  düzəldildiyini qısa yaz.
- **Şəkillər işıqlandırılır (QANUN):** qaranlıq tonlar hər şəklin öz parlaqlığına görə avtomatik
  işıqlandırılır (render.py `brighten`) — əvvəl düzəltmə, sonra işıqlandırma.
- **Sonluq:** yaşıl fon, loqo, "SATILIR", 3 sətir xüsusiyyət (qiymət yox), qızılı telefon düyməsi;
  sonda girişə keçid (loop).
- **Temp (QANUN):** yavaş — hər yazı növbəti keçidə qədər rahat oxunmalıdır. render.py-də minimum:
  giriş kadrı 3.2 san, hər yazılı kadr 2.0 san, son kadr 4.8 san, keçid 0.3 san. Bunları azaltma.
  Kadrları sürətləndirmə.
- **Şəkil seçimi (QANUN, 10-cu qanunla yeniləndi):** video maksimum 25–30 saniyədir; sığmayanda ən zəif
  şəkillər çıxarılır və istifadəçiyə yazılır. Şəkilləri
  məntiqi ardıcıllıqla düz: fasad → həyət/hovuz → giriş/hol → mətbəx → qonaq otağı → yataq otaqları →
  qarderob → sanuzellər.
- **Musiqi:** istifadəçi nömrə deyəndə `"music": "pro:NN"` (`video/music_pro_songs.py`, 1–20).
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
