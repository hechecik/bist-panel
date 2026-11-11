# G14 — KAP bildirim akışı ve yabancı payı

**Önkoşul:** G00
**Özellik:** Bu görev büyük ölçüde **kaynak doğrulama** işi. Uç noktalar gayriresmi olabilir.

## Adımlar
1. **Önce keşif:** KAP (kap.org.tr) bildirim listesi için anahtarsız bir JSON veya HTML kaynağı bul.
   - Örnek yanıtı `tests/fixtures/kap_ornek.json` olarak kaydet.
   - Erişim yoksa ya da robots/ToS engeli varsa **dur ve raporla**. Google News araması mevcut yedek olarak kalır.
2. **Bildirim türleri:** özel durum açıklaması, bedelsiz/bedelli, temettü, pay geri alım, yeni iş ilişkisi, finansal rapor.
   - Hisse kartına son 5 bildirimi bağla (başlık, tarih, link).
   - Bedelsiz bildirimleri G02'deki bölünme dedektörüne çapraz kontrol olarak ver.
3. **Yabancı payı:** Hisse bazında yabancı takas oranı ve 20 günlük değişimi.
   - Kaynak: MKK/BIST yayınları veya İş Yatırım. Önce doğrula.
   - Haftalık güncelleme yeterli.
4. **Hız:** İstekler arasında en az 1 sn bekle. `User-Agent` ayarla. Günlük istek sayısını logla.

## Kabul kriterleri
- [ ] Fixture ile ağsız parse testi var.
- [ ] Kaynak bulunamayan kısım için raporda "neden" yazıyor. Kodda yarım kalmış uç nokta yok.
