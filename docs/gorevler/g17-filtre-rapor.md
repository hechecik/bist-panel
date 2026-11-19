# G17 — Skor Eşiği + Endeks Rejim Filtresi Raporu

**Durum:** TAMAMLANDI · commit `9ce2122` (main) · 313/313 test · canlıda

## Ne yapıldı

`senaryo_uret` / `test_senaryolari` motoruna **giriş filtresi** parametreleri eklendi.
G16'da çıkış kuralı değiştirilerek alfa aranmıştı ve bulunamamıştı; G17 aynı altyapıyla
sinyalin **kendisini** süzdü:

- `min_skor` — skoru eşiğin altında kalan AL sinyalleri hiç işleme alınmaz
- `endeks_rejim: n` — sinyal gününde XU100 kapanışı kendi MA_n'inin altındaysa sinyal atlanır
  (lookahead yok: aynı günün kapanışı kullanılır, karar ertesi gün açılışta uygulanır)
- Endeks serisi MA penceresine yetmiyorsa **uydurma yapılmaz**, senaryo `durum: 'veri yok'` döner
- `en_az_islem = 100` — "en iyi" sıralamasına girmek için asgari işlem sayısı
  (30-60 işlemlik varyantın şans eseri alfa üretmesi engellenir)

## Sonuçlar (gerçek veri, 100 hisse, 2048 referans işlem)

| Senaryo | İşlem | İsabet | Ort. Getiri | Ort. Alfa | PF | Max DD | Devir |
|---|---|---|---|---|---|---|---|
| referans | 2048 | %49,0 | +%0,2 | −%0,1 | 1,07 | %32,8 | 55 |
| stop_yok | 2014 | %50,1 | −%0,0 | −%0,3 | 0,99 | %40,8 | 51 |
| hedef_yok | 2000 | %48,5 | +%0,3 | −%0,1 | 1,10 | %24,9 | 53 |
| cikis_yok | 1973 | %49,2 | +%0,0 | −%0,3 | 1,01 | %41,4 | 50 |
| vade_5 | 2048 | %49,0 | +%0,0 | −%0,3 | 1,01 | %42,4 | 55 |
| vade_10 | 1516 | %46,7 | −%0,1 | −%0,3 | 0,98 | %38,2 | 34 |
| **vade_20** | 1221 | %45,5 | +%0,3 | −%0,0 | 1,07 | **%16,3** | **25** |
| kapanis_giris | 2355 | %49,0 | +%0,1 | −%0,2 | 1,05 | %36,9 | 53 |
| **skor_3** | 1635 | %49,1 | +%0,2 | −%0,1 | 1,06 | **%21,1** | 55 |
| **skor_4** | 727 | %50,1 | +%0,1 | −%0,5 | 1,03 | **%11,6** | 54 |
| rejim (MA50) | 924 | %45,8 | −%0,4 | +%0,0 | 0,87 | %19,9 | 55 |
| rejim_200 | 59 | %30,5 | −%2,9 | +%0,7 | 0,32 | %5,9 | 59 |
| skor_3_rejim | 722 | %46,5 | −%0,3 | −%0,0 | 0,89 | %26,8 | 56 |
| skor_4_rejim | 319 | %44,8 | −%0,6 | −%0,3 | 0,79 | %14,5 | 55 |

`en_iyi` = **vade_20** (alfa −%0,0, DD %16,3).

## Yorum — net

1. **Skor eşiği alfa üretmiyor.** Skor ≥3 ve ≥4 sinyalleri riski sert düşürüyor
   (DD %32,8 → %21,1 → %11,6) ama alfa değişmiyor (−%0,1 / −%0,5). Yani yüksek skor
   "daha az dalgalı" demek, "endeksi yener" demek değil.
2. **Endeks rejim filtresi alfa üretmiyor, üstelik kaliteyi bozuyor.**
   MA50 rejimi alfayı tam olarak 0'a çekiyor (endeksin kendisi kadar) ama PF 0,87'ye düşüyor
   ve ortalama getiri negatife geçiyor (−%0,4). Sebep: filtre portföyü endeksin yükseldiği
   dar pencerelere sıkıştırıyor → hisse seçiciliği kaybı. MA200 rejimi 59 işlemle
   istatistiksel olarak anlamsız (isabet %30,5, PF 0,32) — örneklem yetersiz.
3. **Tekrarlanan tek bulgu risk tarafında.** 20 gün vade (DD %16,3, devir 25) ve skor ≥4
   (DD %11,6) aynı alfayla yarı/dörtte bir risk sunuyor. Stop şart (stopsuz PF 0,99, DD %40,8).
4. **Karar:** sinyal motoru (skor formülü) endeksi geçmiyor; eşik ve rejim filtreleri bunu
   düzeltmiyor. Bir sonraki gerçek iyileştirme sinyal girdilerinde (sektör göreli güç,
   hacim profili, temel analiz ağırlığı) aranmalı — kural/filtre katmanında değil.

## Dosyalar

- `scripts/veri_cek.py` — `min_skor` / `endeks_rejim` parametreleri, rejim serisi hesabı,
  `en_az_islem` eşiği, `durum: 'veri yok'` ayrımı
- `tests/test_g17_filtre_senaryolari.py` — 6 test (ağsız, sentetik seri)
- `js/bolum/karne.js` — "en az 100 işlem şartı" notu
- `sw.js` — CACHE v10 → **v11** (sert yenileme gerekir)
- `data/piyasa.json` — 14 senaryo canlıda doğrulandı
