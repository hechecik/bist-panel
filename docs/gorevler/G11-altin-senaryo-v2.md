# G11 — Altın senaryo motoru v2, gram ayrışımı, altın karnesi

**Önkoşul:** G10
**Ayrıntı:** `docs/analiz/altin_yonerge.md` → yalnızca "C) SENARYO MOTORU v2" bölümü

## Adımlar
1. **Skoru ikiye ayır:**
   - `teknik_skor`: mevcut skor. Momentum üç kez sayılıyor, 52 haftalık konum bileşenini kaldır.
   - `makro_skor`: reel faiz, DXY, dot plot makası, Brent.
   - ⚠️ Eşikler (±10 bp, ±%1, ±%10) **doğrulanmamış başlangıç değerleridir**. Kodda `ESIK_*` sabiti olarak tanımla ve yorum satırıyla belirt.
2. **Çelişki uyarısı:** Teknik ve makro skorun işareti zıtsa "⚠️ ayrışma" uyarısı göster.
3. **Koşullu senaryolar:** Fiyatlanmış / şahin sürpriz / güvercin sürpriz / jeopolitik şok.
   - Her biri "EĞER → gözlenebilir tetik → ons bandı" zinciri olarak yazılır.
   - Bant = ATR×√5 katları.
   - **Olasılık sütunu** sadece vadeli fiyatlamadan türetilebiliyorsa gösterilir.
   - Çakışan durumlar (örneğin şahin Fed + jeopolitik şok) ayrı bir satırda gösterilir.
4. **Gram ayrışımı:** 1 gün, 1 hafta, 1 ay için Δgram ≈ Δons + ΔUSDTRY. UI'da bar olarak göster.
   - Kur varsayımı: son 63 günün ortalama aylık değer kaybı. UI'da yazılı olarak göster.
5. **Altın karnesi:**
   - Her gün TR 23:00'teki çalıştırmada `data/altin_gecmis.json`'a bir satır ekle (en fazla 400 satır).
   - 5 ve 20 gün sonraki isabeti hesapla ve göster.

## Kabul kriterleri
- [ ] `grep -rn "olasilik" scripts/altin_cek.py` sonucu sadece vadeli fiyatlamadan türetilen alanları gösteriyor.
- [ ] Gram ayrışımı ±%0,2 içinde gerçek gram değişimine eşit.
- [ ] Karne 1 satırla başlıyor, gün geçtikçe büyüyor.
