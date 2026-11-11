# G06 — Ön yüzü modüllere bölme (token tasarrufu)

**Önkoşul:** G01–G05 tamamlanmış ya da en azından `index.html`'e dokunan açık dal yok
**Dokunulacak dosyalar:** `index.html` → `css/app.css`, `js/core.js`, `js/bolum/*.js`

## Neden
`index.html` ~90 KB (~30 bin token). Her küçük UI değişikliğinde ajan bu dosyanın tamamını okuyor.

## Kurallar
- **Build adımı yok.** Native ES module kullan (`<script type="module" src="js/main.js">`).
- **Davranış değişmeyecek.** Sadece taşıma yapılıyor. Fonksiyon adları ve DOM id'leri aynı kalacak.
- **Bölüm bölüm ilerle**, her bölüm ayrı commit. Bu görev birden fazla oturuma bölünebilir. Kullanıcı "G06 devam" derse kaldığın yerden devam et (`git log --oneline | grep G06` ile bak).

## Sıra
1. `<style>` içeriğini → `css/app.css`
2. Ortak yardımcılar (`fmt`, `utcTarih`, `alEsc`, sekme yönetimi, fetch) → `js/core.js` (export)
3. Her render fonksiyonunu kendi dosyasına taşı: `js/bolum/piyasa.js`, `grafik.js`, `karne.js`, `haber.js`, `fon.js`, `takvim.js`, `getiri.js`, `kripto.js`, `ict.js`, `altin.js`
4. `index.html`'de sadece iskelet ve `<script type="module">` kalsın.
5. `sw.js` önbellek listesini yeni dosyalarla güncelle. `CACHE` sürümünü artır.

## Kabul kriterleri
- [ ] `index.html` < 10 KB. Her `js/bolum/*.js` dosyası < 15 KB.
- [ ] Yerel testte konsol hatası yok: `python3 -m http.server 8000` ile aç, her sekmeyi tıkla. Mümkünse headless tarayıcıyla kontrol et.
- [ ] `AGENTS.md` dosya haritası tablosu yeni yapıya göre güncellendi.
