# G06 — Rapor (parça 1/4 tamamlandı)

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
- [ ] Her `js/bolum/*.js` < 15 KB → dosyalar **henüz yok** (parça 2/3)
- [x] Yerel testte konsol hatası yok (her sekme tıklandı, headless Chromium)
- [x] `AGENTS.md` dosya haritası güncellendi
