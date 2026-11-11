# G12 — Temel analiz yeniden

**Önkoşul:** G07 (ayrı haftalık görev) önerilir. Zorunlu değil.
**Dokunulacak dosyalar:** `scripts/veri_cek.py` (`temel_analiz`) ya da `scripts/analiz/temel.py`, yeni `data/temel.json`, UI

## Mevcut sorunlar
- Yahoo `.info` verisi BIST için sıklıkla eski veya hatalı.
- Listedeki ilk 30 hisse işleniyor (alfabetik, BIST30 değil).
- 15 dakikada bir 30 istek atılıyor (rate-limit riski).
- Banka ve sanayi F/K'sı aynı ölçekle puanlanıyor.
- TMS 29 enflasyon muhasebesi göz ardı ediliyor.

## Adımlar
1. **Sıklık:** Haftada 1 kez çalışsın, 100 hissenin tamamı için. İstekler arasında 1–2 sn bekle.
2. **Kaynak sırası:**
   - İş Yatırım mali tablo uç noktası. Önce yanıt yapısını doğrula ve örnek yanıtı `tests/fixtures/` altına kaydet.
   - Yedek: Yahoo.
   - Her satırda `kaynak` ve `donem` (bilanço dönemi) alanı olsun.
3. **Metrikler:** F/K, PD/DD, FAVÖK marjı, net borç/FAVÖK, ROE, reel ROE (ROE − yıllık TÜFE), yıllık satış büyümesi (nominal ve reel), temettü verimi.
4. **Puanlama:** Her metriği **sektör medyanına göre** yüzdelik sıraya çevir. Sektör bilgisi `scripts/sektorler.json`'dan alınır. Bankalarda FAVÖK metrikleri atlanır.
5. **Bilanço takvimi:** KAP'tan beklenen açıklama tarihleri. Kaynak doğrulanamazsa bu kısmı atla ve raporla.

## Kabul kriterleri
- [ ] Fixture verisiyle ağsız çalışan bir test var.
- [ ] UI'da her metrik bilanço dönemiyle birlikte gösteriliyor ("2026/9").
- [ ] Sektör medyanı hesaplanamayan (sektörde < 3 hisse) durumlar "kıyas yok" olarak gösteriliyor.
