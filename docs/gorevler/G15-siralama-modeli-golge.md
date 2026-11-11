# G15 — Kesitsel sıralama modeli (gölge mod) ve denetim karnesi

**Önkoşul:** G09 + `data/log/` içinde **≥ 120 işlem günü**. Kontrol: `cat data/log/*.jsonl | wc -l`. 120'den azsa sadece 4. adımı (denetim sekmesi) yap ve dur.
**Ayrıntı:** `docs/analiz/derin_analiz.md` → yalnızca "§5" bölümü

## Adımlar
1. **Model:** Her gün 100 hisse için RS20, RS60, TREND_ATR, MACD_hist/ATR, RSI, HACIM_ORAN, VOL20 (ters), ZIRVE_UZAK özelliklerini **yüzdelik sıraya** çevir.
   - Eşit ağırlıklı ortalama al = `sira_skoru` (0–100).
2. **Özellik seçimi:**
   - Bir özellik, son 120 günlük kayan pencerede IC işareti tutarlıysa modele girer: IC ort / IC std > 0,3.
   - Bu kontrol `sinyal_denetim.py` ile yapılır. Sonuçları `data/model_ozellik.json`'a yaz.
   - Ağırlıklar otomatik optimize **edilmez**.
3. **Gölge mod:**
   - `sira_skoru` hesaplanır ve log'a yazılır.
   - UI'da "deneysel" etiketiyle ayrı bir sütunda gösterilir.
   - Mevcut `skor` ve `sinyal` **değişmez**.
   - Haftalık (Cuma kapanışı) üst %20 ve alt %20 listesi.
4. **Denetim sekmesi (karne altında):**
   - Haftalık çalışan `sinyal_denetim.py --log data/log --ufuk 5 10 20 --json data/denetim.json` çıktısını göster.
   - IC zaman serisi, AL−SAT farkı, eski skor ile sıra skorunun karşılaştırması.
5. **Geçiş kuralı:** UI'da şu not yazsın: sıra skoru, ≥ 6 test ayında IC_IR > 0,3 ve üst-alt farkı > 2× maliyet koşulunu sağlarsa varsayılan yapılabilir, **karar kullanıcıya aittir**.

## Kabul kriterleri
- [ ] Mevcut skor ve sinyal testleri değişmeden geçiyor.
- [ ] `data/denetim.json` haftalık güncelleniyor.
- [ ] UI'da "deneysel" ve "yatırım tavsiyesi değildir" ifadeleri var.
