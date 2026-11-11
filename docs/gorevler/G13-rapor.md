# G13 Raporu — Türkiye risk paneli ve dolar/altın bazlı BIST

**Durum:** tamam (main'e merge edilmedi, `gorev/G13` dalında)
**Test:** 284/284 passed (`.venv/bin/python -m pytest tests -q`) — 258 mevcut + 26 yeni

## 1. Reel BIST

**Seriler:** XU100 G09'un tam endeks serisi (251 bar), USDTRY (`USDTRY=X`, yfinance) ve
gram altın (`altin_cek.gram_serisi` / altın verisi) 1 yıllık. Üçü de **TARİHE göre** hizalanır
(`seri_eslestir`, index'e göre değil — G11 yaklaşımının aynısı). Hedef tarih yoksa en yakın
**önceki** tarih kullanılır; `G13_TOLERANS_GUN = 7` günü aşarsa o gün düşürülür. Gelecek tarihli
değer asla baz alınmaz (bakış ileri sızıntısı yok).

**Getiriler (pencere iş günü, bar):** `1h=5, 1a=21, 3a=63, 1y=252`, YBB = yılın ilk barından.
Son gün seride birebir yoksa getiri üretilmez (eski veri taşınmaz).

**Gerçek çıktı (son bar 2026-11-11, 251 gün, 2025-11-11 → 2026-11-11):**

| Dönem | TL | USD | Gram altın | Aralık |
|---|---|---|---|---|
| 1 hafta | +%1,64 | +%1,20 | +%3,20 | 11-04 → 11-11 |
| 1 ay | −%3,99 | −%5,69 | −%1,06 | 10-12 → 11-11 |
| 3 ay | −%17,68 | −%21,53 | −%12,83 | 08-14 → 11-11 |
| 1 yıl | +%6,81 | −%9,76 | −%7,83 | 2025-11-21 → 11-11 |
| YBB | +%1,46 | −%13,15 | −%5,86 | 2026-01-02 → 11-11 |

**Tutarlılık:** `(1+TL)/(1+USDTRY değ.)−1 ≈ USD` → 5/5 dönem ±%0,1 içinde (en büyük sapma %0,001).

**UI (Piyasa sekmesi):** üç çizgili normalize grafik (dönem başı = 100; TL/USD/altın aynı ölçekte
okunabilsin diye her seri kendi başına 100'e bölünür) + dönem bazlı getiri tablosu
(TL / USD / gram altın + tarih aralığı) + tutarlılık notu. Grafik inline SVG (repoda Chart.js yok).

## 2. Türkiye risk kartı

- **TR 2Y / 10Y:** `getiri.json` → **%39,42 / %35,99** (doviz.com/tahvil). Boşsa `tahvil_durum`
  metni gösterilir, sayı uydurulmaz.
- **Politika faizi:** %36,00 (karar 22.10.2026, uygulama 23.10.2026). **TÜFE yıllık:** %29,77 (10-2026).
- **Reel faiz = %36,00 − %29,77 = +6,23 puan** → POZİTİF (TL mevduat cazip, altın/dövize baskı).
- **PPK takvimi:** TCMB sayfasından parse (`ppk_tarihleri_parse`, Türkçe ay adları, tablo dışı metinden
  tarih üretilmez). Doğrulanan: **sonraki PPK 2026-12-10 · 28 gün kaldı**. Liste: 2026-12-10 ·
  2027-01-21 · 2027-03-18 · 2027-04-22.
- **Rezervler:** kod hazır, **anahtar yok** — `EVDS_KEY` secret'ı eklenmeli. Satırda "anahtar yok" yazıyor.
- **5Y CDS:** anahtarsız güvenilir kaynak bulunamadı → **eklenmedi** (kartta açıkça belirtiliyor).

## 3. Kod değişiklikleri

`scripts/veri_cek.py` (yeni saf fonksiyonlar, `takvim_cek` öncesi):
`seri_eslestir`, `reel_bist_serileri`, `reel_bist_getirileri`, `_g13_getiri`, `reel_faiz`,
`tahvil_getirileri`, `ppk_tarihleri_parse`, `sonraki_ppk`, `tr_risk_blogu` (ağ),
`reel_bist_verisi` (ağ). Sabitler: `G13_TOLERANS_GUN=7`, `G13_DONEM_BAR`, `G13_TUTARLILIK_TOL_PCT=0.1`,
`G13_GRAM_ONS`, `EVDS_SECRET_ADI='EVDS_KEY'`.

`index.html`: `reelBistGrafik`, `reelGetiriTablosu`, `trRiskKarti` + Piyasa sekmesine iki bölüm.
`data/piyasa.json` çıktısına `reel_bist` ve `tr_risk` blokları eklendi.

`tests/test_g13_tr_risk_reel_bist.py`: 26 test — hizalama/tolerans, ileri sızıntı yok, normalize
seriler, pencere barları, YBB sıfır baz, tutarlılık, son gün katı eşleşme, reel faiz (negatif/eksik
girdi), tahvil 2Y/10Y + eksik vade, PPK parse (yıl filtresi, tablo yok, tarih uydurmama), geri sayım,
rezerv anahtar yok, eksik veride sayı uydurmama.

## Bilinen sınırlar

- Gram altın ile hesap gramı arasında %1,09 sapma uyarısı var (altın bölümünde mevcut davranış, G13 dışı).
- PPK sayfası gelecek yıl için okunamazsa yalnız mevcut yıl tarihleri gösterilir; tarih uydurulmaz.
