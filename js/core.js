/* BIST Panel — ortak çekirdek (G06)
   Zaman damgası, sekme yönetimi, biçimlendirme, veri tazeliği/bayat bant ve
   HTML kaçış yardımcıları. Saf taşıma: davranış eski index.html ile aynı.
   Dışa aktarılan her isim main.js tarafından window'a bağlanır. */


function utcTarih(s) {
  if (!s) return new Date(NaN);
  // RFC-2822 ('Wed, 11 Nov 2026 04:23:18 GMT') tarihleri aynen geçerli — 'Z' eklenirse bozulur.
  if (/[a-zA-Z]{3},/.test(s) || /GMT|UTC|[+-]\d\d:?\d\d$|[zZ]$/.test(s)) return new Date(s);
  return new Date(s + 'Z');
}

/* ── SEKME YÖNETİMİ ──
   Sekme tıklanınca bölümün yükleme fonksiyonu çağrılır. Fonksiyonlar main.js
   tarafından window'a bağlandığı için isimle erişilir. */
function sekmeKur() {
  const SEC = document.querySelectorAll('.tab');
  SEC.forEach(t => t.addEventListener('click', () => {
    SEC.forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    document.querySelectorAll('.sec').forEach(s => s.classList.remove('active'));
    document.getElementById('sec-' + t.dataset.sec).classList.add('active');
    if (t.dataset.sec === 'grafik' && typeof tvYukle === 'function') tvYukle();
    if (t.dataset.sec === 'altin') altinYukle();
    if (t.dataset.sec === 'kripto') kriptoYukle();
    if (t.dataset.sec === 'ict') ictYukle();
    if (t.dataset.sec === 'takvim') takvimYukle();
    if (t.dataset.sec === 'fon') getiriYukle();
  }));
}
export { sekmeKur };


const fmt = (n, d=2) => n == null ? '—' : Number(n).toLocaleString('tr-TR', {minimumFractionDigits:d, maximumFractionDigits:d});
const yuzde = n => n == null ? '' : (n >= 0 ? '+' : '') + n.toFixed(2) + '%';
const ok = n => n >= 0 ? 'up' : 'down';


function tazelik(veriTarihi) {
  if (!veriTarihi) return '';
  const gun = Math.floor((Date.now() - new Date(veriTarihi + 'T18:00:00').getTime()) / 86400000);
  if (gun <= 1) return '<span class="fresh ok">BUGÜN</span>';
  return `<span class="fresh">${gun} GÜN ESKİ</span>`;
}

const BAYAT = { hisse: null, altin: null };
function haftaIciIsGunu(ms) {           // ms: geçen süre → aşılan iş günü (tam gün)
  if (!isFinite(ms) || ms < 0) return 0;
  let kalan = ms, isGunu = 0, adim = 0;
  while (kalan >= 86400000 && adim < 400) {
    kalan -= 86400000; adim++;
    const gun = new Date(Date.now() - kalan).getDay();
    if (gun !== 0 && gun !== 6) isGunu++;
  }
  return isGunu;
}
function bayatBantMetni(hisseYasMs, altinYasMs) {
  const parca = [];
  if (isFinite(hisseYasMs) && haftaIciIsGunu(hisseYasMs) > 1)
    parca.push('Hisse verisi ' + Math.floor(hisseYasMs / 3600000) + ' saattir güncellenmedi');
  if (isFinite(altinYasMs) && altinYasMs > 7200000)
    parca.push('Altın verisi ' + Math.floor(altinYasMs / 3600000) + ' saattir güncellenmedi');
  return parca.length ? '⚠️ ' + parca.join(' · ') : '';
}
function bayatBantGuncelle() {
  const el = document.getElementById('bayatBant');
  if (!el) return;
  const simdi = Date.now();
  const hisseYas = BAYAT.hisse ? simdi - BAYAT.hisse.getTime() : NaN;
  const altinYas = BAYAT.altin ? simdi - BAYAT.altin.getTime() : NaN;
  const metin = bayatBantMetni(hisseYas, altinYas);
  if (metin) { el.textContent = metin; el.classList.add('on'); }
  else { el.textContent = ''; el.classList.remove('on'); }
}

const alEsc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pfOk = v => (v >= 0 ? '▲ +' : '▼ ') + Number(v).toFixed(2) + '%';
const pfRenk = v => v >= 0 ? 'var(--up)' : 'var(--down)';


export { utcTarih, fmt, yuzde, ok, tazelik, BAYAT, haftaIciIsGunu, bayatBantMetni,
         bayatBantGuncelle, alEsc, pfOk, pfRenk };
