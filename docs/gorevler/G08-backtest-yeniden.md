# G08 — Backtest ve karnenin yeniden yazılması

**Önkoşul:** G02, G05
**Dokunulacak dosyalar:** `scripts/veri_cek.py` (`test_senaryolari`) ya da G07 sonrası `scripts/analiz/backtest.py`, karne UI
**Ayrıntı:** `docs/analiz/derin_analiz.md` → yalnızca "§5 Doğrulama protokolü" bölümü

## Mevcut testin sorunları
- Çıkış kuralı yok, işlemler "bugüne kadar" tutuluyor.
- Aynı hissede çakışan işlemler ayrı sayılıyor.
- Sermaye simülasyonu ilk 10 işlemi sembol sırasıyla seçiyor (seçim yanlılığı).
- Maliyet yok, endeksle kıyas yok.

## Yeni kurallar
- **Giriş:** Kesin sinyalin ertesi günü açılış. Kilitli günlerde bir sonraki kilitsiz güne kaydır.
- **Çıkış:** 5, 10 ve 20 iş günü sonra **veya** 2×ATR stop / 3×ATR hedef, hangisi önce gelirse.
- **Pozisyon:** Aynı hissede açık pozisyon varken yeni giriş yok.
- **Maliyet:** Gidiş-dönüş `MALIYET = 0.002` (parametre).
- **Benchmark:** Aynı tarihlerde XU100 getirisi. Raporlanan değer: **alfa = işlem getirisi − XU100 getirisi**.
- **Sermaye simülasyonu:** Kronolojik, 100.000 TL, en fazla 10 pozisyon. Nakit olmadığında yeni sinyal atlanır.
- **Metrikler:** işlem sayısı, isabet, ortalama alfa, profit factor, max drawdown, devir. Skor seviyesine göre (2, 3, ≥4) ayrı tablo.
- **Sıklık:** Günde bir kez çalışır (kapanış sonrası).

## Kabul kriterleri
- [ ] `tests/test_backtest.py`: sentetik veride (a) stop tetiklenmesi, (b) vade çıkışı, (c) çakışma engeli, (d) maliyet düşümü test edilmiş.
- [ ] Karne UI'da "ortalama alfa" ve "XU100'e göre" ifadeleri görünüyor.
- [ ] Eski `ortalama` alanı bir sürüm boyunca korunuyor (geriye uyumluluk).
