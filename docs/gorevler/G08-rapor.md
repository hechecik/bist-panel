# G08 — Backtest Yeniden (düzeltme sonrası)

## Ne değişti
- **Motor:** "sinyal → bugüne kadar tut" yerine her sinyal gerçek işlem: ertesi gün açılış girişi, 5/10/20 iş günü vade veya 2×ATR stop / 3×ATR hedef, hangisi önce. Gün içi min/max kontrolü; aynı gün stop+hedef → stop (muhafazakâr); taban kilidinde çıkış ilk kilitsiz güne kayar.
- **Maliyet:** Gidiş-dönüş %0,2 iki taraflı uygulanıyor — `net = (çıkış×(1−MALIYET/2)) / (giriş×(1+MALIYET/2)) − 1`. `stop_getiri_yuzde` aynı formülle. Fiyat değişmezse net ≈ **−%0,2**.
- **Simülasyon:** 100.000 TL, en fazla 10 eşzamanlı pozisyon, kronolojik. Aynı giriş tarihli sinyallerde sıralama **skor azalan**, eşitlikte sembol. Nakit/slot yoksa sinyal atlanır.
- **DD alanı:** `gerceklesen_max_dd_yuzde` (açık pozisyonlar maliyetten sayılır); eski ad `max_drawdown_yuzde` bir sürüm boyunca da yazılıyor. UI etiketi "Gerçekleşen Max Düşüş".
- **Evren:** RİSKLİ/İZLE etiketliler ve yeni halka arzlar hariç (10 hisse çıkarıldı).
- **Benchmark:** Aynı giriş/çıkış tarihlerinde XU100 getirisi (G09 tam serisi). Alfa = işlem getirisi − XU100 getirisi.
- **Maliyet/tolerans testleri:** 148 test geçiyor (6 zorunlu case + maliyet −%0,2, skor önceliği, mutabakat).

## Eski vs yeni (aynı veri, 100 hisse → 90 evren)

- İşlem sayısı: **8.407 → 1.981**
- Ortalama getiri: **−%24,5 → −%0,1**
- Ortalama alfa: **ölçülmüyordu → −%0,3**
- İsabet: **%22,2 → %46,8**
- Profit factor: **— → 0,95**
- Gerçekleşen max düşüş (100K): **— → %39,6**
- Devir: **— → 54,8**
- 100K simülasyon sonucu: **— → 72.830 TL (−27.170 TL)**

> Eski −%24,5 "iyileşme" değil ölçüm farkı: eski kod sinyali son bara kadar tutuyordu (6 ayda −%98'e taşınan hisseler var). Karşılaştırılabilir metrik **alfa** ve hiçbir skor seviyesinde pozitif değil.

## Skor seviyesine göre (XU100'e göre alfa)

- **Skor 2** — 691 işlem · isabet %45,7 · ort. getiri −%0,2 · alfa **−%0,4** · PF 0,92 · DD %33,2
- **Skor 3** — 950 işlem · isabet %47,1 · ort. getiri −%0,1 · alfa **−%0,2** · PF 0,95 · DD %37,4
- **Skor ≥4** — 340 işlem · isabet %48,2 · ort. getiri −%0,0 · alfa **−%0,4** · PF 1,00 · DD %12,6

Skor ≥4'ün düşük DD'si sinyal kalitesinden değil, 3 kat az işlem açmasından.

## Sermaye simülasyonu mutabakatı

- Simülasyona giren işlem: **721** (ertesi gün açılış senaryosu), atlanan 1.260
- Giren işlemlerin ortalama getirisi: **−%0,38** (721 işlem × 10.000 TL sabit tahsis)
- Beklenen kâr Σ(tahsis × getiri): **−27.170 TL**
- Simülasyon kâr/zarar: **−27.170 TL**
- **Fark: 0 TL (%0,000)** — %1 eşiğinin çok altında. Sebep: tahsis sabit (sermaye/max_pozisyon) ve bileşik büyüme yok; her işlem aynı 10.000 TL ile giriyor, dolayısıyla Σ(tahsis×getiri) birebir kapalı forma eşit. Fark yaratacak tek durum tahsisin sermayeye göre yeniden hesaplanması olurdu; görev tanımı sabit tahsis istiyor, değiştirilmedi.
- Pazar günü açılış senaryosu: 369 işlem · −640 TL (fark 0) · DD %19,9
- Stop'lu senaryo: 119 işlem · −90.570 TL (fark 0) · DD %89,5

## Ekran görüntüsü doğrulaması
Tarayıcıda: "Performans — XU100'e göre" kartı, skor tablosu, "Gerçekleşen Max Düşüş (100K)" etiketi ve çıkış tarihli işlem tablosu hatasız render ediliyor; konsol hatası yok.

## Dosyalar
- `scripts/veri_cek.py` — parametre bloğu, `hisse_verisi_cek()`, `uygun_evren()`, `_islem_hesapla()`, `sermaye_simule()`, `test_senaryolari()`, `backtest_gercek_veri()`, `main()`
- `index.html` — XU100 alfa kartı, skor tablosu, işlem tablosu kolonları, "Gerçekleşen Max Düşüş" etiketi
- `tests/test_g08_backtest_yeniden.py` — 12 test (6 zorunlu + maliyet −%0,2, skor önceliği, mutabakat)
- `tests/test_g05_backtest_kilit.py` — ATR bazlı stop assertion
- `data/*.json` commit dışı

## Durum
`gorev/G08` dalında 2 commit (`d1bd8a6`, `45268d8`). **main'e merge edilmedi** — onay bekliyor.
