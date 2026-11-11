/* js/bolum/grafik.js — GRAFİK bölümü (G06 parça 2)
   renderGrafik + TradingView widget kurulumu (tvYukle) ve piyasa tablosundaki
   📈 butonunun açtığı mum grafiği modalı (grafikModal/grafikKapat).
   Davranış birebir eski main.js ile aynı; window bağları dosya sonunda. */

/* ══════════ MUM GRAFİK MODALI (TradingView) ══════════ */
function grafikModal(sym) {
  document.getElementById('modalSym').textContent = sym + ' · 15 dk mum';
  const m = document.getElementById('grafikModal');
  m.style.display = 'flex';
  const el = document.getElementById('modalWidget');
  el.innerHTML = '';
  const s = document.createElement('script');
  s.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
  s.async = true;
  s.innerHTML = JSON.stringify({
    autosize: true, symbol: 'BIST:' + sym, interval: '15', timezone: 'Europe/Istanbul',
    theme: 'dark', style: '1', locale: 'tr', hide_side_toolbar: false,
    allow_symbol_change: false, save_image: false,
    studies: ['Volume@tv-basicstudies'], container_id: 'modalWidget'
  });
  el.appendChild(s);
}
function grafikKapat() {
  document.getElementById('grafikModal').style.display = 'none';
  document.getElementById('modalWidget').innerHTML = '';
}

/* ══════════ GRAFİK (2 — TradingView, saniyelik canlı) ══════════ */
export function renderGrafik(d) {
  // 15 dk'da bir yukle() çağrılır — kullanıcının seçimini koru, widget'ı
  // sadece sekme GÖRÜNÜRKEN yeniden embed et (display:none iken autosize:true
  // 0 yükseklik üretir, grafik boş görünür).
  const mevcutSym = (document.getElementById('tvSym') || {}).value || '';
  const mevcutInt = (document.getElementById('tvInt') || {}).value || '';
  const sec = document.getElementById('sec-grafik');
  const aktifMi = sec.classList.contains('active');
  const hisseler = [...(d.sinyaller.al||[]), ...(d.sinyaller.tut||[]), ...(d.sinyaller.sat||[])].map(r => r.sembol);
  const opt = (v, etiket, secili) => `<option value="${v}" ${secili ? 'selected' : ''}>${etiket}</option>`;
  let html = `<h2>📈 Canlı Grafik <span class="cnt">TradingView</span></h2>` +
    `<div class="toolbar"><select id="tvSym" onchange="tvYukle()">` +
    opt('BIST:XU100', 'BIST 100 (XU100)', !mevcutSym || mevcutSym === 'BIST:XU100') +
    hisseler.map(s => opt('BIST:' + s, s, mevcutSym === 'BIST:' + s)).join('') +
    `</select><select id="tvInt" onchange="tvYukle()">` +
    opt('1', '1 dk', mevcutInt === '1') + opt('5', '5 dk', mevcutInt === '5') +
    opt('15', '15 dk', !mevcutInt || mevcutInt === '15') + opt('60', '1 saat', mevcutInt === '60') +
    opt('D', 'Günlük', mevcutInt === 'D') + opt('W', 'Haftalık', mevcutInt === 'W') +
    `</select></div>` +
    `<div id="tvWidget" style="height:480px;border:1px solid var(--bd);border-radius:12px;overflow:hidden;background:var(--bg2)"></div>` +
    `<div class="note">TradingView embed — saniyelik canlı mum grafiği (key'siz, ücretsiz). Tablolar seans içinde periyodik güncellenir, grafik canlıdır. Seans dışında son kapanış görünür.</div>`;
  sec.innerHTML = html;
  if (aktifMi) tvYukle(); // sekme açıkken widget'ı görünür boyutta embed et
}
function tvYukle() {
  const el = document.getElementById('tvWidget');
  if (!el) return;
  const sym = document.getElementById('tvSym').value;
  const interval = document.getElementById('tvInt').value;
  el.innerHTML = '';
  const s = document.createElement('script');
  s.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
  s.async = true;
  s.innerHTML = JSON.stringify({
    autosize: true, symbol: sym, interval: interval, timezone: "Europe/Istanbul",
    theme: "dark", style: "1", locale: "tr", hide_side_toolbar: false,
    allow_symbol_change: false, save_image: false,
    studies: ["Volume@tv-basicstudies"], container_id: "tvWidget"
  });
  el.appendChild(s);
}

/* ── window bağları (inline onclick/onchange için) ── */
Object.assign(window, { grafikModal, grafikKapat, renderGrafik, tvYukle });
