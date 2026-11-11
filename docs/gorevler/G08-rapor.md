# G08 — Backtest Yeniden

## Özet
Backtest motoru "sinyal → bugüne kadar tut" mantığından çıkarıldı; artık her sinyal **gerçek bir işlem** olarak açılıp kapanıyor: ertesi gün açılış girişi, 5/10/20 iş günü vade veya 2×ATR stop / 3×ATR hedef, %0,2 gidiş-dönüş maliyet, XU100'e göre alfa ve kronolojik 100.000 TL sermaye simülasyonu.

**Sonuç iyileştirilmedi** — ne çıktıysa o raporlandı. Özet: strateji XU100'ü geçemiyor (ortalama alfa −%0,2), kronolojik simülasyonda 100K TL → 71.810 TL.

## Eski vs Yeni (aynı veri, RİSKLİ/İZLE hariç 89 hisse, 2025-05-29 → 2026-11-11)

| Metrik | Eski (`ertesi_gun_acilis`) | Yeni (`ertesi_gun_acilis`) |
|---|---|---|
| İşlem sayısı | 8.407 | **1.981** |
| Ortalama getiri | **−%24,5** | **−%0,0** (≈ 0) |
| Kazanan / kaybeden | 1.9K / 6.4K (~%22 isabet) | 939 / 1.042 (~%47,4 isabet) |
| Ortalama alfa (XU100'e göre) | ölçülmüyordu | **−%0,2** |
| Profit factor | — | 0,99 |
| Max drawdown (100K) | — | %37,9 |
| Devir (yıllık) | — | 54,8 |
| 100K TL sonuç (kronolojik) | 107.610 TL (10 işlem, eşzamanlılık yok) | **71.810 TL** (708 işlem, 1.273 atlanan) |

İşlem sayısındaki düşüş (8.407 → 1.981) **aynı hissede açık pozisyon varken yeni giriş yasağı**ndan geliyor: eskiden her gün aynı hisse için ayrı "işlem" üretiliyordu (TKFEN tek başına 3 kez), şimdi pozisyon kapanana kadar yeni işlem açılmıyor.

Ortalama getirinin −%24,5 → −%0,0 olması **iyileşme değil, ölçüm farkı**: eski metrik her sinyali son bara kadar tutuyordu (6 ay boyunca düşen hisse −%98'e kadar taşınıyordu), yeni metrik vade/stop ile kapanıyor. Kıyaslanabilir metrik **alfadır** ve o da negatif (−%0,2).

## Skor seviyesine göre (yeni)

| Skor | İşlem | İsabet | Ort. getiri | Ort. alfa (XU100'e göre) | Profit factor | Max DD | Devir |
|---|---|---|---|---|---|---|---|
| 2 | 691 | %46,2 | −%0,1 | −%0,3 | 0,95 | %31,7 | 55,0 |
| 3 | 950 | %47,4 | −%0,0 | −%0,1 | 0,99 | %31,7 | 54,5 |
| ≥4 | 340 | %50,0 | +%0,1 | −%0,3 | 1,04 | %11,4 | 55,1 |

Skor yükseldikçe isabet artıyor (%46,2 → %50,0), profit factor 1'in üstüne çıkıyor (skor ≥4: 1,04) ama **alfa hiçbir seviyede pozitife dönmüyor**. Skor ≥4 en düşük drawdown'u üretiyor (%11,4 vs %31,7) — bunun nedeni işlem sayısının 3 kat az olması, sinyal kalitesi değil.

## Sermaye simülasyonu (kronolojik, 100K TL, max 10 pozisyon, 10K tahsis)

| Senaryo | İşlem | Atlanan | Sonuç | Max DD |
|---|---|---|---|---|
| Pazartesi | 369 | 49 | 100.420 TL | %18,8 |
| Ertesi gün açılış | 708 | 1.273 | **71.810 TL** | %37,9 |
| Stop senaryosu | 120 | 295 | 9.950 TL | %89,3 |

## Değişen dosyalar

**`scripts/veri_cek.py`** (+~420/−~89):
- Dosya başına G08 parametre bloğu: `MALIYET=0.002`, `BT_VADE_GUN=(5,10,20)`, `BT_ATR_STOP=2.0`, `BT_ATR_HEDEF=3.0`, `BT_SERMAYE=100_000.0`, `BT_MAX_POZISYON=10`
- `hisse_verisi_cek(liste)` — 3 kademeli failover (İş Yatırım → borsapy → yfinance) `main()` içinden çıkarıldı; hem canlı panel hem backtest aynı zinciri kullanıyor
- `uygun_evren(hisse_veri, sinyaller)` — RİSKLİ/İZLE etiketli hisseler (10 hisse: DSTKF, ESEN, EUREN, GRSEL, IEYHO, ODINE, PATEK, RALYH, REEDR, SARKY) ve ilk 60 barı doldurmamış yeni halka arzlar hariç; çıktıda `haric` alanı ile hangi hissenin neden çıkarıldığı yazılıyor
- `_islem_hesapla(sembol, i, s, ind, kilitler)` — tek sinyal → tek kapanmış işlem. Giriş ertesi gün açılış (`ilk_kilitsiz`, G05 kuralı), çıkış gün içi min/max ile stop/hedef, aynı gün ikisi de tetiklenirse **stop** (muhafazakâr), taban kilidinde çıkış ilk kilitsiz güne kayar. Net getiri = `çıkış×(1−MALIYET/2)/giriş − 1`
- `sermaye_simule(islemler, ...)` — kronolojik, 100.000 TL, en fazla 10 eşzamanlı pozisyon, nakit yoksa sinyal atlanır (`atlanan` sayacı), günlük equity → max drawdown
- `test_senaryolari(hisse_veri, endeks_serisi=None)` — yeni opsiyonel parametre; `metrik`, `skor_tablosu`, `parametre`, `benchmark`, `haric` alanları eklendi. **Eski alanların tamamı korundu** (`ertesi_gun_acilis`, `ortalama`, `kazanan`, `stop_calismis`, `bugun`, `max_dusus` bir sürüm daha)
- `main()` — `endeks_verisi()` sonucundaki G09 tam serisi (`seri`) backtest'e geçiriliyor

**`index.html`** (+45): "Performans — XU100'e göre" kart bloğu (ortalama alfa, işlem getirisi, isabet, profit factor, max drawdown, devir), skor seviyesi tablosu, parametre dipnotu. "En Kârlı İşlemler" tablosuna **Çıkış / Neden / Alfa (XU100'e göre)** kolonları eklendi. Eski karne ve simülasyon kartları aynen duruyor.

**`tests/test_g08_backtest_yeniden.py`** (yeni, 9 test): stop tetiklenmesi, vade çıkışı, çakışma engeli, maliyet düşümü, aynı gün stop+hedef → stop, taban kilidinde çıkış kayması (hem `_islem_hesapla` hem `test_senaryolari` üzerinden), kritik alanların korunması, endeks yokken `None` güvenliği.

**`tests/test_g05_backtest_kilit.py`** (±8): stop artık −%5 sabit değil ATR tabanlı; `stop_getiri_yuzde == -5.0` iddiası `stop_fiyat` ile tutarlılık kontrolüne çevrildi.

## Testler
`.venv/bin/python -m pytest tests -q` → **145 passed** (136 mevcut + 9 yeni). Ağa çıkmıyor, sentetik seri ile deterministik.

Test yazarken 2 hata çıktı, ikisi de test verimden: (1) seri 5 bardan kısaydı, vade sonu oluşmuyordu; (2) −%2,1 beklerken kod −%2,098 döndürüyordu — 1 ondalığa yuvarlanınca −%2,1 oluyor, iddia hassasiyeti düzeltildi.

## Kabul kriterleri
- [x] Giriş ertesi gün açılış, kilitli günde ilk kilitsiz güne kayma
- [x] Çıkış 5/10/20 iş günü veya 2×ATR stop / 3×ATR hedef, hangisi önce
- [x] Stop/hedef gün içi max/min ile; aynı gün ikisi de → stop
- [x] Taban kilidinde çıkış ilk kilitsiz güne kayar
- [x] Aynı hissede açık pozisyon varken yeni giriş yok
- [x] `MALIYET = 0.002` dosya başında parametre
- [x] Benchmark XU100, aynı giriş/çıkış tarihleri, alfa = işlem getirisi − XU100 getirisi
- [x] Kronolojik sermaye simülasyonu (100K, max 10 pozisyon, nakit yoksa atla)
- [x] Metrikler + skor seviyesi (2, 3, ≥4) tabloları
- [x] Eski alanlar korundu, UI yeni alanları "XU100'e göre" etiketiyle gösteriyor
- [x] RİSKLİ/İZLE hariç, yeni halka arzlar istatistik dışı
- [x] 6 zorunlu test + 3 ek test
- [x] `data/*.json` commit'e katılmadı
- [x] main'e merge edilmedi

## Kısıtlar
- RİSKLİ/İZLE etiketleri sinyal anındaki güncel etiketlerden geliyor (tarihsel etiket geçmişi tutulmuyor) — ileriye dönük yanlılık riski var, bu yüzden hariç tutulan hisseler `haric` alanında tek tek listeleniyor.
- ATR yoksa (nadir, <15 bar) girişin %2'si varsayılıyor.
- Endeks serisi yoksa alfa `null` döner, uydurma yapılmaz.
- Vade, kilitli günleri de sayıyor (takvim günü değil işlem günü); taban kilidi vadeyi ötelerse `vade_gun` 20'yi aşabilir (ör. PASEU 25 gün).

## Notlar
- `data/*.json` commit'e katılmadı.
- Branch: `gorev/G08`. **main'e merge edilmedi** — onay bekleniyor.
