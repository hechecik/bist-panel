# G13 — Türkiye risk paneli ve dolar/altın bazlı BIST

**Önkoşul:** G00
**Dokunulacak dosyalar:** `scripts/veri_cek.py` (`makro_fiyatlar` yanına yeni fonksiyonlar), UI piyasa sekmesi

## 1. Reel BIST (en yüksek öncelik)
- XU100 / USDTRY ve XU100 / gram altın serileri (1 yıl).
- Getiriler: 1 hafta, 1 ay, 3 ay, 1 yıl, YBB (yılbaşından beri). Hem nominal TL hem USD hem altın bazında.
- UI'da üç çizgili bir grafik ve getiri tablosu.

## 2. Türkiye risk kartı
- **TR 2Y/10Y getiri:** `getiri.json` tahvil verisi. Boşsa bunu belirt.
- **Politika faizi** (mevcut) ve **reel faiz** = politika faizi − yıllık TÜFE (mevcut veriden).
- **TCMB rezervleri:** EVDS API'si ücretsiz anahtar gerektirir. Secret adı `EVDS_KEY`. Secret yoksa bu satırda "anahtar yok" yaz, kodu yine de hazırla.
- **5Y CDS:** Anahtarsız güvenilir bir kaynak bulunamazsa **ekleme**, raporda belirt.
- **PPK takvimi + geri sayım:** Tarihler TCMB sayfasından parse edilsin. Tahmin edilmesin.

## Kabul kriterleri
- [ ] Reel BIST getirileri birbiriyle tutarlı: (1 + TL getirisi) / (1 + USDTRY değişimi) − 1 ≈ USD getirisi (±%0,1).
- [ ] Anahtar veya kaynak yoksa ilgili satırda açıklama var, uydurma değer yok.
