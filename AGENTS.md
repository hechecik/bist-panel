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
0. **Kullanıcı onayı olmadan yeni workflow dosyası oluşturma veya silme.** `.github/workflows/` altındaki dosya kümesi sabittir: `veri-cek.yml`, `altin-cek.yml`, `kripto-cek.yml`, `ek-veri-cek.yml`. Geçici teşhis/test workflow'u açmak da bu kurala tabidir.
1. **LLM veya ücretli API çağrısı ekleme.** Site çalışırken sıfır token harcar. Bütün yorum metinleri sayılardan deterministik şablonlarla üretilir.
2. **Uydurma sayı yok.** Her sayı gerçek bir kaynaktan gelir. Veri alınamazsa `"durum": "veri yok"` yazılır, tahmini veya elle girilmiş değer kullanılmaz. Elle olasılık yüzdesi yazmak yasak.
3. **Zaman damgaları** timezone-aware UTC ISO formatında yazılır (`dt.datetime.now(dt.timezone.utc)`). UI'da gösterim `timeZone:'Europe/Istanbul'` ile yapılır. JS'de tarih ayrıştırmak için `utcTarih()` yardımcısı kullanılır.
4. **Her veri bloğu bağımsız try/except içinde çalışır.** Bir kaynak düşerse diğerleri yazılmaya devam eder.
5. Her bölümde **"Yatırım tavsiyesi değildir"** notu kalır.
6. **API anahtarı, token veya şifre koda ya da repoya yazılmaz.** Gerekiyorsa GitHub Secrets kullanılır ve kullanıcıya hangi secret'ın ekleneceği söylenir.

## Dosya haritası
| Yol | İçerik | Not |
|---|---|---|
| `index.html` | Ön yüz iskeleti (HTML + `<script type="module" src="js/main.js">`) | 3,2 KB — sadece nav + boş `<section>`'lar |
| `css/app.css` | Tüm stiller (eski `<style>` içeriği) | `grep -n "^\.\|^#" css/app.css` ile sınıf ara |
| `js/main.js` | Giriş noktası: core + bölüm import'ları, `init()`, 15 dk `setInterval`, SW kaydı | 5,7 KB — render fonksiyonu **yok** |
| `js/core.js` | Ortak yardımcılar: `utcTarih`, `fmt`, `yuzde`, `ok`, `alEsc`, `pfOk/pfRenk`, `tazelik`, bayat bant, `sekmeKur`, paylaşılan `durum` | Hepsi export edilir |
| `js/bolum/piyasa.js` | `renderPiyasa`, özet kartlar, makro, gece analizi, tablo kurulumu | Piyasa sekmesinin girişi (9,6 KB) |
| `js/bolum/piyasa-tablo.js` | `KOLONLAR`, `hisseSatir`, `tabloBolum` | Satır + detay satırı HTML'i (4,8 KB) |
| `js/bolum/piyasa-filtre.js` | `filtrele`, `csvIndir` | Arama/sinyal/trend/squeeze filtresi, CSV (2,6 KB) |
| `js/bolum/piyasa-yardimci.js` | `badge`, `g05Cipleri`, `rsiYorum`, `hacimOranHtml`, `genislikHtml`, `mfiYorum`, `trendHtml`, `squeezeHtml`, `sparkSVG` | Tablo hücre yardımcıları (12,1 KB) |
| `js/bolum/piyasa-reel.js` | `reelBistGrafik`, `reelBistTablo`, `trRiskHtml` | G13 reel BIST + TR risk kartı (6,8 KB) |
| `js/bolum/portfoy.js` | Portföy + fiyat alarmları (localStorage), `alarmKontrol` | `PIYASA_VERI`'yi canlı import eder (6,4 KB) |
| `js/bolum/grafik.js` | `renderGrafik`, `tvYukle`, `grafikModal/Kapat` | TradingView mum modalı (4,1 KB) |
| `js/bolum/karne.js` | `renderSenaryo`, karne tabloları | `karne-risk.js`'i import eder (11,5 KB) |
| `js/bolum/karne-risk.js` | `riskHesapKur`, `riskDoldur`, `riskStopYuzde`, `riskHesapla` | Risk/pozisyon hesaplayıcı (5,4 KB) |
| `js/bolum/haber.js` | `renderHaber`, `haberFiltrele`, `chip`, `zamanGecmis` | Haber filtreleri + mini takvim (5,9 KB) |
| `js/bolum/fon.js` | `renderFon` — fon risk iştahı, getiri, dağılım, temel analiz | (4,9 KB) |
| `js/bolum/getiri.js` | `getiriYukle` — tahvil/eurobond | (2,8 KB) |
| `js/bolum/takvim.js` | `takvimYukle` — halka arz/temettü | (3,3 KB) |
| `js/bolum/kripto.js` | `renderKripto`, `kriptoYukle`, `krFiyat`, `krBuyuk` | `KRIPTO_VERI` burada (5,2 KB) |
| `js/bolum/ict.js` | `renderIct`, `ictYukle`, `ictListe`, `ictYon` | ICT taraması (8,1 KB) |
| `js/bolum/altin.js` | `renderAltin`, `altinYukle` | `ALTIN_VERI` burada (13,9 KB) |
| `js/bolum/altin-makro.js` | `altinMakroHtml` — makro/FOMC bloğu | altin.js'ten import edilir (7,0 KB) |
| `sw.js` | Service worker: `CACHE` sürümü + `CORE` önbellek listesi | **Yeni `js/bolum/` dosyası eklersen `CORE`'a da yaz ve `CACHE` sürümünü artır** |
| `scripts/veri_cek.py` | Hisse verisi, sinyal, backtest, haber, fon, temel analiz | ~55 KB. `grep -n "^def "` ile fonksiyonu bul |
| `scripts/indikatorler.py` | RSI, MACD, BB, MFI, OBV, ATR, sinyal skoru | |
| `scripts/ict.py` | ICT tarayıcı (MSS, FVG, OB, sweep) | |
| `scripts/altin_cek.py` | Altın verisi → `data/altin.json` | |
| `scripts/kripto_cek.py` | CoinGecko → `data/kripto.json` | |
| `scripts/getiri_cek.py`, `scripts/takvim_cek.py` | Tahvil/eurobond, halka arz/temettü | |
| `scripts/sinyal_denetim.py` | Sinyallerin ileri getiri denetimi (IC, AL−SAT farkı) | Ağ bağlantısı gerekmez |
| `data/*.json` | Üretilen veri | **Bütün olarak okuma.** `python3 -c "import json;d=json.load(open('data/X.json'));print(list(d))"` veya `jq` ile alan seç |
| `data/log/*.jsonl` | Günlük tam kesit sinyal kaydı (100 hisse) | Denetimin ham verisi |
| `.github/workflows/*.yml` | veri-cek (15 dk), altin-cek (30 dk), kripto-cek (30 dk), ek-veri-cek (2×/gün) | Hepsi `workflow_dispatch` içerir; harici tetikleme cron-job.org → fine-grained PAT (Actions: write) |
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

## Raporlama kuralı
Raporlar AGENTS.md'ye YAZILMAZ; `docs/gorevler/GXX-rapor.md` dosyasına yazılır ve Telegram'a kısa özet gönderilir.
