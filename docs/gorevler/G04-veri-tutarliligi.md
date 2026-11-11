# G04 — Piyasa verisi tutarlılığı ve küçük hatalar

**Önkoşul:** G00
**Dokunulacak dosyalar:** `scripts/veri_cek.py`, `scripts/getiri_cek.py`, `bist100.txt`, `index.html` (ilgili render fonksiyonları)

## Adımlar
1. **Gram altın tutarlılığı (`makro_fiyatlar`):**
   - Kanıt: 10 Kasım'da gram 6.675 TL (+%1,8) görünüyordu, ama ons 4.036$ (−%1,9) × USD/TL 50,18 hesabı ≈ 6.512 TL veriyor. borsapy'den gelen gram değeri bayat.
   - Düzeltme: Gram = ons / 31.1035 × USD hesapla. borsapy değerini `capraz` alanına yaz. Fark %1'i aşarsa `uyari: true` yap, UI'da ⚠️ göster.
2. **Tahvil boş:** `getiri.json → tahvil: []` dönüyor. `bp.bonds()` boş geliyor.
   - Boşsa `"tahvil_durum": "kaynak boş — <hata özeti>"` yaz.
   - UI tahvil kısmında bu durumu göster, sessizce gizleme.
   - Alternatif kaynak dene (doviz.com tahvil sayfası parse). Bulamazsan raporla.
3. **bist100.txt:**
   - Dosyanın ilk satırına `# guncelleme: YYYY-MM-DD` ekle. Yorum satırları okunurken atlansın.
   - Fallback listesinde KCHOL iki kez geçiyor, tekrarı sil.
4. **`hisse_bazli.max_dusus`:** Aslında "en kötü işlem getirisi" ve pozitif değer alabiliyor (GARAN +7,2). Alanı `en_kotu_islem` olarak yeniden adlandır. UI etiketini de buna göre değiştir.
5. **Haber sıralaması:** Bütün `yayin_tarihi` değerlerini UTC ISO formatına çevir (saat dilimi olmayanları UTC kabul et), sonra sırala. Şu an string sıralaması yapılıyor.

## Kabul kriterleri
- [ ] `piyasa.json → makro.fiyatlar.gram-altin` içinde `capraz` ve `uyari` alanları var.
- [ ] `getiri.json` tahvil boşken `tahvil_durum` alanı dolu.
- [ ] `grep -c KCHOL scripts/veri_cek.py` fallback listesinde 1 kez geçiyor.
- [ ] Testlerin hepsi geçiyor.
