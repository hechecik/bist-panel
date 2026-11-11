# G03 — Altın sekmesi: kalan hatalar

**Önkoşul:** G00
**Dokunulacak dosyalar:** `scripts/altin_cek.py`, `index.html` (`renderAltin` fonksiyonu → `grep -n "function renderAltin" index.html`)
**Yamada çözülmüş olanlar (tekrar yapma):** gün adı kayması, ÜFE anahtar kelimesi, saat bazlı tekrarlar, haber tarihi gösterimi, UTC zaman damgası.

## Adımlar
1. **Takvim penceresi:** `kritik_gunler(21)` → `kritik_gunler(45)`. Sıralama önce önem derecesi (high > mid), sonra tarih olsun. Sonra `[:14]` ile kırp.
   - Ayrıca `scripts/fomc_tarihleri.json` dosyasını oku (yoksa oluştur) ve FOMC karar günlerini sınır uygulamadan **her zaman** listeye ekle.
   - Tarihleri https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm sayfasından parse et. Parse başarısız olursa JSON'daki değerleri kullan.
   - **Tarih tahmin etme.** 2026 için bilinen tarih: 8–9 Aralık.
2. **Spot fiyat:** Manşet ons ve gram altın SPOT fiyattan hesaplansın: `gram = spot / 31.1034768 * usdtry`. GC=F sadece tarihsel seri için kullanılsın. Spot yoksa GC=F'ye düş ve `fiyat.kaynak_tipi = "vadeli"` yaz. UI'da "vadeli" rozeti göster.
3. **Tazelik rozeti:** Şu an `<span class="fresh ok">` sabit. Hafta içi `uretildi` 90 dakikadan eskiyse `fresh` rozeti "bayat" sınıfına geçsin.
4. **Metin uyumsuzlukları:**
   - Senaryo metnindeki "hacimle kırıp" ifadesini "kırıp üstünde kapanırsa" yap. Kodda hacim kontrolü yok.
   - Alt nottaki "trend eğimi" ifadesini "1 aylık performans" yap.
5. **Seviye seçimi:**
   - 50'lik yuvarlak seviyeleri kaldır, sadece 100'lükler kalsın.
   - Senaryo tetiği fiyattan en az 0,5×ATR uzakta olsun. Hedef, tetikten en az 1×ATR ötede olsun.
   - Her senaryoya `gecersiz` (geçersizlik seviyesi) alanı ekle.

## Kabul kriterleri
- [ ] `data/altin.json → kritik_gunler` içinde 9 Aralık FOMC kaydı var.
- [ ] `fiyat.gram_tl` ≈ `spot/31.1035*usdtry` (fark < %0,1).
- [ ] `abs(senaryo.yukari.tetik - fiyat.ons) >= 0.5 * vital.atr` ve aynı koşul aşağı tetik için de sağlanıyor.
- [ ] `python3 scripts/altin_cek.py` hatasız çalışıyor (ağ bağlantısı gerekir).
