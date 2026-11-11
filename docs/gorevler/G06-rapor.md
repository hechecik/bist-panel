# G06 — Rapor (parça 4/4 tamamlandı — görev kapandı)

## Nerede kaldım (parça 4 — tamam)
- `main.js` içinde kalanlar taşındı: `js/bolum/kripto.js` (5.218 B — `renderKripto`, `kriptoYukle`, `krFiyat`, `krBuyuk`, `KRIPTO_VERI`), `js/bolum/ict.js` (8.121 B — `renderIct`, `ictYukle`, `ictListe`, `ictYon`), `js/bolum/altin.js` (13.858 B — `renderAltin`, `altinYukle`, `ALTIN_VERI`) + `js/bolum/altin-makro.js` (7.038 B — `altinMakroHtml`, altin.js'ten import).
- 15 KB sınırı için `piyasa.js` de alt modüllere ayrıldı: `piyasa-yardimci.js` (12.103 B), `piyasa-tablo.js` (4.799 B), `piyasa-filtre.js` (2.724 B), `piyasa-reel.js` (6.9 KB), `portfoy.js` (6.360 B), `karne-risk.js` (5.4 KB).
- `js/main.js` **546 satır / 37.272 B → 102 satır / 5.725 B** — sadece import + `init()` + `yukle()` + ziyaretçi göstergesi. Render fonksiyonu yok.
- `sw.js`: CACHE `bist-panel-v4` → **`bist-panel-v5`**, CORE'a 6 yeni alt modül eklendi (`karne-risk, piyasa-filtre, piyasa-reel, piyasa-tablo, piyasa-yardimci, portfoy`). Eksik olsalardı offline modda 404 alınırdı.
- **Bulunan gerçek hata (uygulama kodunda düzeltildi):** detay satırı hiç üretilmiyordu. `piyasa-tablo.js` `durum.detay.get(r.sembol)` ile karşılaştırıyordu ama `durum.detay` hiç doldurulmuyordu (`git log -S` ile tüm geçmişte doldurma kodu yok — UI v2'de toggle listener'ı eklenmiş, veri bağı eklenmemiş). `main.js` `yukle()` içinde `durum.detay` sinyal gruplarından (al/tut/sat/izle/riskli) dolduruluyor; `hisseSatir` artık kayıt yoksa satır verisini kullanıyor → detay satırı 24 hissede açılıyor.

### Headless E2E (Playwright, gerçek DOM) — 8/8 PASS
| Kontrol | Sonuç |
|---|---|
| 9 sekme | **PASS** — piyasa=72.903 · grafik=3.576 · altın=25.250 · kripto=25.311 · senaryo=15.299 · haber=49.858 · takvim=13.924 · fon=15.553 · ict=20.558 |
| Modal aç/kapa | **PASS** — `#pfSym` sembolü ENERY, `display flex → none` |
| Filtre (arama + sinyal) | **PASS** — tümü=24 → AK=3 → geri=24 → TUT=10 |
| CSV | **PASS** — `bist-panel-2026-11-11.csv`, 25 satır, 3.237 B |
| Portföy ekle/sil | **PASS** — ekle=['THYAO'], P&L=+0 TL, sil → [] |
| Risk hesabı | **PASS** — giriş 14,10 / stop 12,96 → 2.631 lot (beklenen 2631), 37.097 TL pozisyon |
| Satır detayı aç/kapa | **PASS** — ENERY `table-row → none → table-row`, içerik «📋 Tüm Nedenler RSI 57 → güçlü ama aşırı değil…» |
| Konsol temiz | **PASS** — pageerror=[], konsol=[] (TradingView 403 hariç) |

### Test seçici düzeltmeleri
- `#pfSembol` → gerçek id **`#pfSym`** (portföy giriş alanı); portföy listesi kapsayıcısı tablo değil `.pf-row` div'leri, ayrı liste id'si yok.
- Satır detayı tıklaması: `element.click()` yerine Playwright fare tıklaması (`position 5,5`) + `display` ölçümü.
- Filtre: `fill()` sonrası `dispatch_event("input")` şart (`oninput` özniteliği programatik fill ile tetiklenmiyor); sayım `style.display !== 'none'` ile.

### pytest
- `.venv/bin/python -m pytest tests -q` → **284 passed in 2.71s**
- `node --check` → `js/*.js`, `js/bolum/*.js` (19 dosya) + `sw.js` temiz; `py_compile scripts/*.py` OK.

## Nerede kaldım (parça 3 — tamam, commit 87d7f00)
- `js/main.js` 814 satır / 52.954 B → **546 satır / 37.272 B**.
- Taşınanlar: `js/bolum/haber.js` (5.948 B — renderHaber, `haberFiltre` state, KAT_AD, `zamanGecmis`, `haberFiltrele`, `chip`; aşırı satım/alım taraması + mini takvim bu dosyada), `js/bolum/fon.js` (4.931 B — renderFon, fon risk iştahı/getiri/dağılım/sektör/temel analiz), `js/bolum/getiri.js` (2.843 B — `getiriYukle`, tahvil + eurobond), `js/bolum/takvim.js` (3.327 B — `takvimYukle`, halka arz + temettü).
- Bölüm dosyaları kendi `window.*` bağlarını kuruyor (`renderHaber`, `haberFiltrele`, `chip`, `renderFon`, `getiriYukle`, `takvimYukle`) — inline onclick bozulmadı.
- `sw.js`: CACHE `bist-panel-v3` → **`bist-panel-v4`**, CORE'a 4 bölüm dosyası eklendi.
- **Doğrulama:** 284 test passed; `node --check` 10 dosyada temiz; headless Chromium'da 9 sekme tıklandı, konsol hatası/unhandled rejection yok; haber filtreleri ölçüldü (tümü 49.843 B → BIST 17.504 B → EN 22.806 B → Pozitif 11.685 B → geri 49.843 B); `zamanGecmis` ve `getiriYukle` elle çağrıldı, hatasız.
- **Sırada (parça 4):** `main.js` içinde kalan kripto (`renderKripto`, `kriptoYukle`, `krFiyat`, `krBuyuk`, `KRIPTO_VERI`), ICT (`renderIct`, `ictYukle`, `ictListe`, `ictYon`), altın (`renderAltin`, `altinYukle`, `ALTIN_VERI`) → `js/bolum/{kripto,ict,altin}.js`. Altın bloğu en büyüğü (~245 satır). Sonrasında `AGENTS.md` dosya haritası güncellenecek ve kabul kriterleri kapanacak.

## Nerede kaldım (parça 2 — tamam)
- `js/main.js` 1603 satır / 104.902 B → **814 satır / 52.954 B**.
- Taşınanlar: `js/bolum/piyasa.js` (33.508 B, 533 satır — badge/g05 yardımcıları, reelBist*, trRisk, hisseSatir/tabloBolum, `durum`, PIYASA_VERI, renderPiyasa, grafikModal/Kapat, filtrele, csvIndir, portföy+alarmlar), `js/bolum/grafik.js` (4.134 B, 74 satır), `js/bolum/karne.js` (16.441 B, 220 satır).
- main.js bunları import edip window'a bağlıyor; bölüm dosyaları kendi window bağlarını kuruyor (inline onclick/oninput/onchange bozulmadı).
- `sw.js`: CACHE `bist-panel-v3`, CORE'a 3 bölüm dosyası eklendi.
- Doğrulama: 284 test passed; 9 sekme tıklanır, konsol hatası yok; modal, filtre, CSV, portföy ekle/sil, risk hesabı elle test edildi.
- **Sırada (parça 3):** haber / fon / takvim / getiri, ardından kripto / ICT / altın bölümleri.

## Nerede kaldım (sonraki oturum için)

**Tamamlanan (parça 1):**
- `<style>` → `css/app.css` (16.126 B taşındı, içerik birebir aynı).
- Ortak yardımcılar → `js/core.js` (3.720 B, hepsi `export`):
  `utcTarih`, `fmt`, `yuzde`, `ok`, `alEsc`, `pfOk`, `pfRenk`, `tazelik`,
  `BAYAT`, `haftaIciIsGunu`, `bayatBantMetni`, `bayatBantGuncelle`, `sekmeKur`.
  - Sekme yönetimi artık `sekmeKur()` fonksiyonu (eski IIFE `SEC.forEach` bloğu).
    Sekme başına yükleme çağrıları (`altinYukle`, `kriptoYukle`, `ictYukle`,
    `takvimYukle`, `getiriYukle`, `tvYukle`) isimle yapılıyor — main.js bunları
    `window`'a bağladığı için davranış aynı.
- `index.html` artık `<script type="module" src="js/main.js">` yükler.
- `js/main.js`: core'u import eder, eski global fonksiyonları `Object.assign(window, …)`
  ile bağlar (inline `onclick`/`onchange` ve `sekmeKur` için gerekli), sonra
  `init()` içinde `sekmeKur()`, `zyYukle()`, `yukle()`, `kriptoYukle()`,
  `altinYukle()`, üç `setInterval` (15 dk) ve service worker kaydını çalıştırır.
- `sw.js`: `CACHE` `bist-panel-v1` → `bist-panel-v2`; `CORE` listesine
  `/css/app.css`, `/js/main.js`, `/js/core.js` eklendi.
- `AGENTS.md` dosya haritası yeni yapıya göre güncellendi.

**Sıradaki (parça 2/3/4):** `js/main.js` içindeki render fonksiyonlarını
`js/bolum/{piyasa,grafik,karne,haber,fon,takvim,getiri,kripto,ict,altin}.js`
dosyalarına taşı; her dosya kendi `window` bağlarını kursun, main.js sadece
import + `init()` kalsın. Ondan sonra `index.html` < 10 KB hedefi zaten sağlanmış olur.
Bölüm dosyaları arasında paylaşılan durum: `PIYASA_VERI`, `ALTIN_VERI`,
`KRIPTO_VERI`, `haberFiltre`, `BAYAT` (core'da), `durum` — taşırken bunları
core'a ya da küçük bir `js/state.js`'e almak gerekecek.
`yukle()` fonksiyonu tüm render'ları çağırıyor (piyasa/grafik/senaryo/haber/fon) —
parçalarken bu çağrıları main.js'te `import` üzerinden toplamak en temizi.

## Ölçümler

| Dosya | Önce | Sonra |
|---|---|---|
| `index.html` | 125.657 B | **3.167 B** |
| `css/app.css` | — | 16.305 B |
| `js/core.js` | — | 3.720 B |
| `js/main.js` | — | 104.902 B (parça 2/3'te küçülecek) |
| `sw.js` | 1.154 B | 1.261 B |

## Doğrulama

- `python3 -m py_compile scripts/*.py` → OK
- `python3 -m pytest tests -q` → **284 passed**
- Yerel `python3 -m http.server` + Playwright (headless Chromium):
  - 9 sekmenin tamamı tıklandı, hepsinde `active` ve içerik render edildi
    (piyasa 41 KB, grafik, altın 25 KB, kripto 25 KB, karne 15 KB,
    haber 50 KB, takvim 14 KB, getiri 16 KB, ICT 21 KB innerHTML).
  - Konsol: **JS hatası yok.** Tek `console` hatası TradingView embed'inin
    iframe kaynaklı 403'ü (`/support/support-portal-problems/`) — bu dış
    kaynaklı, taşımadan önce de aynı; sayfa koduna ait değil.
  - core: `window.fmt(1234.5)` → `1.234,50`; `utcTarih('2026-11-11 19:01')` → `2026-11-11T19:01:00.000Z`;
    `alEsc('<a&b>')` → `&lt;a&amp;b&gt;`.
  - Inline `onclick` yolu: satırdaki 📈 butonu → modal `display:flex` + doğru sembol;
    ✕ butonu → `display:none`. `oninput="filtrele()"` → 100 satır 24'e düştü.
  - `sw.js`: `bist-panel-v2` aktif, önbellekte 6 dosya; çevrimdışı reload'da
    sayfa + CSS + JS önbellekten geldi (`body` arka planı `rgb(11,14,20)`), hata yok.

## Kabul kriterleri
- [x] `index.html` < 10 KB → **3,1 KB**
- [x] Her `js/bolum/*.js` < 15 KB → en büyük `altin.js` 13.858 B (19 dosya)
- [x] `js/main.js` sadece import + init → **102 satır / 5.725 B**
- [x] Servis worker CORE listesi tüm modülleri kapsıyor (`bist-panel-v5`)
- [x] Headless E2E: 9 sekme / modal / filtre / CSV / portföy / risk / satır detayı / konsol → **8/8 PASS**
- [x] Yerel testte konsol hatası yok (her sekme tıklandı, headless Chromium)
- [x] `AGENTS.md` dosya haritası güncellendi
