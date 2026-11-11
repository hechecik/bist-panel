# bist-panel — Ajan Kuralları

**Dil kuralı:** Kullanıcıya yazılan tüm mesajlar, ara durum bildirimleri ve raporlar Türkçe olacak. Kod, değişken adları ve commit mesajları mevcut düzende kalabilir.

BIST, altın ve kripto piyasa paneli. GitHub Pages üzerinde statik site. Veri GitHub Actions ile çekiliyor.
Canlı adres: https://hechecik.github.io/bist-panel/

## Görev sistemi
- Görevler `docs/gorevler/` klasöründe, her biri ayrı dosyada (`G01-...md`, `G02-...md`).
- Kullanıcı "G05" yazarsa sadece `docs/gorevler/G05-*.md` dosyasını oku ve uygula. Başka görev dosyası açma.
- Görev dosyasında "Önkoşul" varsa önce `git log --oneline | grep "G0X"` ile önkoşulun tamamlandığını kontrol et. Tamamlanmamışsa dur ve kullanıcıya bildir. **G00 manueldir; repoda AGENTS.md varsa G00 tamamlanmış sayılır.**
- Ayrıntılı gerekçe gerekirse `docs/analiz/` altındaki dosyalardan **sadece görevde adı geçen bölümü** oku.

## Değişmez ilkeler
1. **LLM veya ücretli API çağrısı ekleme.** Site çalışırken sıfır token harcar. Bütün yorum metinleri sayılardan deterministik şablonlarla üretilir.
2. **Uydurma sayı yok.** Her sayı gerçek bir kaynaktan gelir. Veri alınamazsa `"durum": "veri yok"` yazılır, tahmini veya elle girilmiş değer kullanılmaz. Elle olasılık yüzdesi yazmak yasak.
3. **Zaman damgaları** timezone-aware UTC ISO formatında yazılır (`dt.datetime.now(dt.timezone.utc)`). UI'da gösterim `timeZone:'Europe/Istanbul'` ile yapılır. JS'de tarih ayrıştırmak için `utcTarih()` yardımcısı kullanılır.
4. **Her veri bloğu bağımsız try/except içinde çalışır.** Bir kaynak düşerse diğerleri yazılmaya devam eder.
5. Her bölümde **"Yatırım tavsiyesi değildir"** notu kalır.
6. **API anahtarı, token veya şifre koda ya da repoya yazılmaz.** Gerekiyorsa GitHub Secrets kullanılır ve kullanıcıya hangi secret'ın ekleneceği söylenir.

## Dosya haritası
| Yol | İçerik | Not |
|---|---|---|
| `index.html` | Tüm ön yüz (CSS + JS tek dosyada, ~90 KB) | **Bütün olarak okuma.** Önce `grep -n "function render" index.html`, sonra ilgili satır aralığını oku |
| `scripts/veri_cek.py` | Hisse verisi, sinyal, backtest, haber, fon, temel analiz | ~55 KB. `grep -n "^def "` ile fonksiyonu bul |
| `scripts/indikatorler.py` | RSI, MACD, BB, MFI, OBV, ATR, sinyal skoru | |
| `scripts/ict.py` | ICT tarayıcı (MSS, FVG, OB, sweep) | |
| `scripts/altin_cek.py` | Altın verisi → `data/altin.json` | |
| `scripts/kripto_cek.py` | CoinGecko → `data/kripto.json` | |
| `scripts/getiri_cek.py`, `scripts/takvim_cek.py` | Tahvil/eurobond, halka arz/temettü | |
| `scripts/sinyal_denetim.py` | Sinyallerin ileri getiri denetimi (IC, AL−SAT farkı) | Ağ bağlantısı gerekmez |
| `data/*.json` | Üretilen veri | **Bütün olarak okuma.** `python3 -c "import json;d=json.load(open('data/X.json'));print(list(d))"` veya `jq` ile alan seç |
| `data/log/*.jsonl` | Günlük tam kesit sinyal kaydı (100 hisse) | Denetimin ham verisi |
| `.github/workflows/*.yml` | veri-cek (15 dk), altin-cek (30 dk), kripto-cek (30 dk), ek-veri-cek (2×/gün) | |
| `tests/` | Ağ bağlantısı gerektirmeyen pytest testleri | |

## Çalışma kuralları (token tasarrufu)
- Dosya okumadan önce `grep -n` ile yeri bul, sonra sadece gereken satır aralığını oku (en fazla ~150 satır).
- Bir görevde değiştirmen gerekmeyen dosyayı açma.
- Uzun komut çıktılarını `| tail -30` veya `| head -50` ile kısalt.
- Görev bitince kodu tekrar baştan okuma. Testleri çalıştır ve raporla.

## Test ve doğrulama
```bash
python3 -m py_compile scripts/*.py
python3 -m pytest tests -q
python3 scripts/sinyal_denetim.py --git . --ufuk 5 10 | tail -25   # isteğe bağlı
```
Yeni bir saf fonksiyon (ağa çıkmayan) eklediysen `tests/` altına testini de ekle.

## Git akışı
0. **Görev başında:** `git checkout -- data/ && git clean -fd data/log/` ile yerel veri değişikliklerini at, sonra `git pull`. `data/` dosyaları asla commit'e katılmaz; veriyi Actions üretir.
1. `git checkout -b gorev/GXX`
2. Değişiklikleri yap ve testleri çalıştır.
3. `git commit -m "GXX: kısa açıklama"`. Mesajda görev kodu mutlaka geçsin.
4. `git push -u origin gorev/GXX`
5. **main dalına kullanıcı onayı olmadan merge etme.**

## Bitiş raporu (Telegram'a kısa yaz)
```
GXX ✅ / ⚠️ / ❌
Değişen dosyalar: ...
Testler: N/N geçti
Kabul kriterleri: [x] ... [ ] ... (karşılanmayan varsa nedeni)
Kullanıcının yapması gereken: ... (yoksa "yok")
```

## G11 DÜZELTME — Gram ayrışımı pencereleri + tek yön bant gösterimi

**Hata (bulundu ve düzeltildi):** `donem_degisimleri()` çağrıları yanlış iş günü pencereleriyle
yapılıyordu: `1h = 21` bar (~1 ay), `1a = 252` bar (~356 takvim günü ≈ **1 yıl**). Bu yüzden
1a kur değişimi %18,62 çıkıyordu — aylık varsayım %1,65 iken imkânsız (≈11 aylık birikim).
Hizalama da index bazlıydı; USDTRY serisinde boşluk olduğunda ons ile aynı tarihe denk gelmiyordu.

**Düzeltmeler:**
1. `DONEM_BAR = {'1g': 1, '1h': 5, '1a': 21}` — pencereler iş günü bazında tanımlandı.
2. `_tarih_key()`, `_seri_eslestir()` — ons ve kur serileri **TARİHE** göre hizalanır; bir seride
   tarih yoksa en yakın **önceki** tarih kullanılır, `HIZALAMA_TOLERANS_GUN = 5` günden eskiyse
   "veri yok" döner (uydurma yok).
3. `gram_serisi()` — ons ve kurdan **BAĞIMSIZ** gram serisi üretir; `gram_gercek_kontrol()` gerçek
   gram değişimini bu seriden alır, böylece aynı pencere hatası tekrarlanmaz.
   Sapma paydası: `tolerans = 0.2 + |Δons%·Δkur%|/100` (yaklaşık formülün karesel çapraz terimi).
4. `kur_tutarlilik_uyarisi()` — pencere kur değişimi, aylık varsayımın `KUR_UYARI_KAT = 3`
   katından büyükse `⚠️` uyarı üretir (eşik %4,953); ayrışma çıktısına `tutarlilik` alanı eklendi.
5. Jeopolitik şok satırı yönü "yukarı" iken artık tek yön gösterilir: `bant_gosterim = [üst, üst]`
   → arayüzde "≈ 4406$ (tek yön)"; şahin (alt) / güvercin (üst) satırlarıyla tutarlı.

**Düzeltilmiş canlı değerler (2026-11-11, ons 4007,00 $ · USDTRY 50,2282):**
- **1g** (1 bar, 2026-11-10 → 11-11): ons 4030,20→4007,00 (−%0,56) · kur 50,2157→50,2282 (+%0,02) · gram 6506,65→6470,80 (**−%0,54**)
- **1h** (5 bar, 2026-11-04 → 11-11): ons 4073,00→4007,00 (−%1,61) · kur 50,0102→50,2282 (+%0,43) · gram 6548,84→6470,80 (**−%1,18**)
- **1a** (21 bar, 2026-10-13 → 11-11): ons 4177,30→4007,00 (−%4,07) · kur 49,3385→50,2282 (**+%1,80**) · gram 6626,32→6470,80 (**−%2,27**)

1a penceresi 29 takvim günü · kur +%1,80 ↔ aylık varsayım %1,65 → tutarlı, uyarı yok.
Kontrol: gerçek gram −%2,338 vs yaklaşık −%2,264 → sapma %0,073 (tolerans %0,2) → **kabul**.
Önceki hatalı çıktı (kur +%18,62, gram +%14,61) tamamen gitti.

**Test:** 256/256 passed (211 önceki + 45 yeni/regresyon). Yeni testler: pencere sabitleri,
tarihe göre hizalama + boşluk/5 gün kuralı, bağımsız gram serisi kontrolü, kur tutarlılık uyarısı
(aylık varsayımın 3 katı), jeopolitik tek yön gösterimi, `seri_degisim` sıfır baz davranışı.
