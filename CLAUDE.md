# Xəzər Sahil Əmlak — ev elanı videoları

Bu repo Xəzər Sahil Əmlak üçün satılan evlərin TikTok / Instagram videolarını hazırlayır.
İstifadəçi ilə **azərbaycan dilində** danışılır.

## İş qaydaları (QANUN — istifadəçi təsdiqləyib)

1. **Şəkillər 1 və ya 2 hissədə göndərilir.** Hər hissə gələndə yalnız qısa təsdiq yaz
   ("✅ 1-ci hissəni aldım: N şəkil") və gözlə. Heç bir emal etmə.
2. **İcazəsiz başlama.** Bütün şəkillər gəldikdən sonra istifadəçidən icazə al
   (və ya istifadəçi özü "başla" desin). Yalnız bundan sonra render et.
3. İstifadəçi "heçnə yazma" desə, yalnız "✅" ilə cavab ver.

## Brend şablonu (DƏYİŞMİR — hər ev üçün eyni)

Təsdiqlənmiş nümunə: istifadəçinin göndərdiyi 4:5 kadr (Mərdəkan villa, "Hovuzlu villa").
Bütün dizayn `video/render.py`-də sabitdir — yeni ev üçün onu dəyişmə, yalnız `listing.json` yaz.

- **Loqo (sol yuxarı, bütün kadrlarda):** yaşıl ikon + "Xəzər Sahil" (ağ) "Əmlak" (qızılı) +
  "REAL ESTATE" (tünd yaşıl, DejaVu Sans Bold). Mənbə: `logo/xezer-sahil-emlak-horizontal-transparent.png`.
  Brend adı **Xəzər Sahil Əmlak** (Xəzər Sahil Ev yox).
- **Rənglər:** yaşıl `#163E3A`, qızılı `#C2A365`, krem `#F1EFE8`, CTA qutusu `#0F2E2A`.
- **Şriftlər** (`video/fonts/`): başlıq Playfair Display Bold, mətn Montserrat 600/700,
  CTA qutusu DejaVu Sans / DejaVu Sans Bold. Ölçülər render.py-dəki kimi qalır.
- **Giriş kadrı:** ən yaxşı fasad şəkli + 2 sətirli başlıq (1-ci krem, 2-ci qızılı) +
  alt sətir (yer • sot • otaq) + qızılı "QİYMƏTİ SONDA ↓" düyməsi.
- **CTA qutusu (aşağıda, bütün kadrlarda):** tünd yaşıl, qızılı çərçivə; üst sətir CTA mətni,
  alt sətir böyük ağ telefon nömrəsi (`010-310-03-02` formatında, defislə).
- **Şəkillər işıqlandırılır:** hər şəkil öz parlaqlığına görə avtomatik (render.py `brighten`).
- **Sonluq:** yaşıl fon, loqo, "SATILIR", qiymət + ₼, 3 sətir xüsusiyyət, qızılı telefon düyməsi;
  sonda girişə keçid (loop).
- **Formatlar:** 9:16 (TikTok/Reels/Story) və 4:5 (Instagram post), ~22 san, 30fps, səssiz audio
  trek (trend səsi istifadəçi tətbiqdə əlavə edir).

## Hər ev üçün dəyişənlər (`video/listings/<slug>/listing.json`)

Başlıq (məs. "Hovuzlu / villa"), alt sətir, qiymət, 3 xüsusiyyət sətri, CTA mətni,
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
