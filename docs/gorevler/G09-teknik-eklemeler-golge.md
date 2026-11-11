# G09 — Teknik eklemeler (gölge mod: skoru DEĞİŞTİRME)

**Önkoşul:** G00 (tam kesit log çalışıyor olmalı)
**Dokunulacak dosyalar:** `scripts/indikatorler.py`, `scripts/veri_cek.py` (`tam_kesit_log` alanları), UI hisse kartı, `scripts/sinyal_denetim.py`

## Neden
41 günlük ölçümde RSI'ın IC'si pozitif çıktı (+0,085 / 5 gün). Yani momentum çalışıyor. Sistem ise RSI<30'a +1 puan veriyor ve bu hisseler 10 günde piyasanın %9,9 altında kaldı. Ama örneklem küçük. **Bu yüzden skor değiştirilmeyecek.** Yeni göstergeler hesaplanıp kaydedilecek, karar 120 günlük log birikince verilecek.

## Eklenecek göstergeler (`tum_indikatorler` içine)
- `RS20`, `RS60`: hisse / XU100 oranının 20 ve 60 günlük değişimi (%). Endeks serisi `endeks_verisi()` içinden tam seri olarak döndürülmeli.
- `HACIM_ORAN`: bugünkü hacim / 20 günlük medyan.
- `VOL20`: 20 günlük günlük getiri std (%).
- `ZIRVE_UZAK`: kapanış / 252 günlük en yüksek − 1.
- `TREND_ATR`: (kapanış − SMA50) / ATR14.

## Piyasa genişliği (`piyasa.json → genislik`)
- MA50 üstündeki hisse yüzdesi, yükselen/düşen oranı, 52 haftalık yeni zirve/dip sayısı. 100 hissenin tamamından hesaplanır.

## Kayıt ve denetim
- Yeni alanları `tam_kesit_log` satırlarına ekle.
- `sinyal_denetim.py → ozellikler` sözlüğüne de ekle.

## Kabul kriterleri
- [ ] `skor` ve `sinyal` hesabında **hiçbir değişiklik yok**. Mevcut testler aynen geçiyor.
- [ ] Yeni göstergeler için sentetik veri testleri var.
- [ ] UI hisse kartında RS20 ve hacim oranı görünüyor. Genişlik kartı piyasa sekmesinde.
