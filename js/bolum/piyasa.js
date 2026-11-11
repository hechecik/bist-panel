/* js/bolum/piyasa.js — PİYASA bölümü (G06 parça 2)
   Taşınanlar: biçimlendirme/rozet yardımcıları, renderPiyasa, genişlik blokları,
   filtre + CSV. Ayrıca ayrıldı: tablo satırı → piyasa-tablo.js, reel BIST +
   TR risk kartı → piyasa-reel.js, portföy + alarmlar → portfoy.js.
   Davranış birebir eski main.js ile aynı; window bağları dosya sonunda. */
import { fmt, yuzde, ok, tazelik, alEsc, pfOk, pfRenk, durum, PIYASA_VERI, setPIYASAVeri } from '../core.js';
import { reelBistGrafik, reelBistTablo, trRiskHtml } from './piyasa-reel.js';
import { KOLONLAR, hisseSatir, tabloBolum } from './piyasa-tablo.js';
import { filtrele, csvIndir } from './piyasa-filtre.js';
import { badge, g05Cipleri, rsiYorum, hacimOranHtml, genislikHtml, mfiYorum, trendHtml, squeezeHtml, sparkSVG } from './piyasa-yardimci.js';

/* durum artık core.js'te: döngüsel import zincirini kırar */
export { durum, PIYASA_VERI };

/* ══════════ PİYASA ══════════ */
export function renderPiyasa(d) {
  setPIYASAVeri(d);
  const e = d.endeks;
  if (e) {
    document.getElementById('exVal').textContent = fmt(e.deger, 2);
    const chg = document.getElementById('exChg');
    chg.innerHTML = `<span class="${ok(e.degisim_yuzde)}">${yuzde(e.degisim_yuzde)}</span> gün`;
    document.getElementById('exSub').innerHTML =
      `<span>📅 ${e.tarih}</span><span>🔍 ${d.sinyaller.toplam} hisse</span><span>📡 ${d.kaynak}</span>` +
      (d.saglik ? `<span class="${d.saglik.durum === 'OK' ? 'up' : 'down'}">🩺 ${d.saglik.durum}${d.saglik.sorunlar.length ? ' · ' + d.saglik.sorunlar.join(', ') : ''}</span>` : '');
  }
  const s = d.sinyaller;
  const alSay = (s.al||[]).length, tutSay = (s.tut||[]).length, satSay = (s.sat||[]).length;
  const izleSay = (s.izle||[]).length, riskliSay = (s.riskli||[]).length;
  // G05 md.3 — geçici: seans sürüyor veya kapanış verisi henüz gelmedi (18:30'a kadar)
  const durumEtiket = s.durum ? ` · <span class="${s.durum === 'kesin' ? 'up' : 'warn'}" title="${s.durum === 'kesin' ? 'Bar kapandı, sinyal kesinleşti' : 'Seans sürüyor veya kapanış verisi henüz gelmedi (18:30\'a kadar)'}">${s.durum === 'kesin' ? '✅ kesin' : '⏳ geçici'}</span>` : '';
  document.getElementById('ozetKartlar').innerHTML =
    `<div class="card"><div class="t">🟢 AL</div><div class="v up">${alSay}</div></div>` +
    `<div class="card"><div class="t">🟡 TUT</div><div class="v" style="color:var(--tx2)">${tutSay}</div></div>` +
    `<div class="card"><div class="t">🔴 SAT</div><div class="v down">${satSay}</div></div>` +
    `<div class="card"><div class="t">⚪ İZLE</div><div class="v" style="color:var(--tx2)">${izleSay}</div></div>` +
    `<div class="card"><div class="t">⚠️ RİSKLİ</div><div class="v down">${riskliSay}</div></div>` +
    `<div class="card"><div class="t">📊 Analiz</div><div class="v">${s.toplam}${durumEtiket}</div></div>`;

  const m = d.makro || {};
  let mk = '';
  Object.values(m.fiyatlar || {}).forEach(f => {
    // ters: VIX gibi endekslerde artış negatiftir (korku) → renk ters
    const ts = f.ters ? -1 : 1;
    const renk = f.degisim == null ? '' : ((f.degisim * ts) >= 0 ? 'up' : 'down');
    // gram altın uyarısı: borsapy çapraz değeri ile hesap arasında >%11 fark
    const gramUyari = f.uyari ? ' <span class="up" title="borsapy çapraz: ' + fmt(f.capraz) +
      ' · fark %' + fmt(f.fark_yuzde) + '">[1]</span>' : '';
    mk += `<div class="mk"><div class="t">${f.ad}${gramUyari}</div><div class="v">${fmt(f.fiyat)}</div>` +
          `<div class="d ${renk}">${f.degisim == null ? f.birim : yuzde(f.degisim)}</div></div>`;
  });
  document.getElementById('makroRow').innerHTML = mk;

  let tcmb = '';
  if (m.faiz && m.faiz.faiz) {
    const reel = m.faiz.faiz - (m.tufe ? m.tufe.yillik : 0);
    const yorum = reel > 0 ? 'POZİTİF reel faiz → altına baskı, TL mevduat cazip' : 'NEGATİF reel faiz → altın/döviz talebi güçlü';
    const karar = m.faiz.karar_tarihi ? `Karar ${m.faiz.karar_tarihi} · uygulama ${m.faiz.tarih}` : `Tarih ${m.faiz.tarih}`;
    tcmb = `<h2>🏛️ Merkez Bankası</h2><div class="tcmb">Politika faizi <b>%${m.faiz.faiz.toFixed(2)}</b> (${karar}) · ` +
           `TÜFE yıllık <b>%${m.tufe ? m.tufe.yillik.toFixed(2) : '?'}</b> · Reel faiz <b class="${ok(reel)}">%${reel >= 0 ? '+' : ''}${reel.toFixed(2)}</b> → ${yorum}</div>`;
  }

  let html = tcmb;
  // G13 — reel BIST (TL/USD/gram altın) + TR risk kartı
  if (d.reel_bist && d.reel_bist.durum === 'ok') {
    html += reelBistGrafik(d.reel_bist);
    html += reelBistTablo(d.reel_bist);
  } else if (d.reel_bist) {
    html += '<h2>💵 Reel BIST</h2><div class="empty">' + alEsc(d.reel_bist.not || d.reel_bist.hata || 'veri yok') + '</div>';
  }
  html += trRiskHtml(d.tr_risk);
  // 5 — Gece analizi (kompakt, daraltılabilir)
  const g = d.gece_analizi;
  if (g) {
    const chip = (liste, renk, alan) => liste.length
      ? '<div class="chips">' + liste.map(x => `<span class="chip"><b style="color:${renk}">${x.sembol}</b> ${fmt(x.fiyat)} <span class="r">${alan === 'rsi' ? 'RSI ' + fmt(x.rsi,0) : 'skor ' + (x.skor>0?'+':'') + x.skor}</span></span>`).join('') + '</div>'
      : '<div class="empty" style="padding:4px 0">Yok</div>';
    html += `<details class="gece"><summary>🌙 Gece Analizi · Yarın İçin <span class="cnt">${g.tarih || ''}</span><span class="ic">▾ aç/kapa</span></summary><div class="ic-body">` +
      `<div class="k">💪 En Güçlü AL Adayları (skor ≥ 3)</div>${chip(g.guclu_al || [], 'var(--up)', 'skor')}` +
      `<div class="k">⚠️ En Zayıf SAT Adayları (skor ≤ -3)</div>${chip(g.zayif_sat || [], 'var(--down)', 'skor')}` +
      `<div class="k">🧲 Bollinger Sıkışma (kırılım izlenecek)</div>${chip((g.squeeze || []).map(x=>({sembol:x.sembol, fiyat:x.fiyat, skor:0})), 'var(--warn)', 'skor')}` +
      `<div class="k">🔵 Aşırı Satım (RSI &lt; 30)</div>${chip((g.asiri_satim || []).map(x=>({sembol:x.sembol, fiyat:x.fiyat, rsi:x.rsi})), 'var(--info)', 'rsi')}` +
      `<div class="k">📅 Yarının Yüksek Önemli Olayları</div>` +
      ((g.yarin_yuksek_onem || []).length
        ? '<div class="chips">' + g.yarin_yuksek_onem.map(o => `<span class="chip"><b class="hi">${o.saat || ''}</b> ${o.ulke || ''} · ${o.olay}</span>`).join('') + '</div>'
        : '<div class="empty" style="padding:4px 0">Yarın için yüksek önemli olay yok</div>') +
      `</div></details>`;
  }

  // 3+6 — Portföy + alarmlar
  html += genislikHtml(d.genislik);
  html += portfoyHtml();

  html += `<div class="toolbar">
    <input id="arama" type="search" placeholder="🔍 Hisse ara (örn. THYAO)…" oninput="filtrele()">
    <select id="fSinyal" onchange="filtrele()">
      <option value="">Sinyal: Tümü</option>
      <option value="AL">AL</option><option value="DİKKAT_AL">DİKKAT AL</option>
      <option value="TUT">TUT</option><option value="DİKKAT_SAT">DİKKAT SAT</option>
      <option value="SAT">SAT</option>
      <option value="IZLE">İZLE (filtre)</option><option value="RISKLI">RİSKLİ</option>
    </select>
    <select id="fTrend" onchange="filtrele()">
      <option value="">Trend: Tümü</option>
      <option value="YUKARI">YUKARI</option><option value="YATAY">YATAY</option><option value="AŞAĞI">AŞAĞI</option>
    </select>
    <select id="fSqueeze" onchange="filtrele()">
      <option value="">Squeeze: Tümü</option>
      <option value="SIKIŞMA">🧲 SIKIŞMA</option><option value="KIRILIM">🚀 KIRILIM</option>
    </select>
    <button class="btn" onclick="csvIndir()">⬇ CSV</button>
  </div>`;

  html += tabloBolum('AL ADAYLARI', '🟢', s.al || []);
  html += tabloBolum('İZLEME / TUT', '🟡', s.tut || []);
  html += tabloBolum('SAT / DİKKAT', '🔴', s.sat || []);
  // G05 — filtreye takılanlar ayrı bölümde (md.2 likidite, md.5 tedbir, md.6 sorunlu hisse)
  if ((s.izle || []).length) html += tabloBolum('FİLTRE — İZLE', '⚪', s.izle || []);
  if ((s.riskli || []).length) html += tabloBolum('RİSKLİ — SORUNLU HİSSE', '⚠️', s.riskli || []);

  html += '<div class="note">' +
    (s.toplam ? `📊 ${s.toplam} hisse analiz edildi · veri ${s.al && s.al[0] && s.al[0].tarih ? s.al[0].tarih : ''} ${s.al && s.al[0] ? tazelik(s.al[0].tarih) : ''} · ` : '') +
    'Yatırım tavsiyesi değildir. Sinyaller teknik indikatör kombinasyonlarıdır.</div>';
  document.getElementById('sec-piyasa').innerHTML = html;
  durum.detay = new Map();
  document.querySelectorAll('#sec-piyasa tbody tr[data-sym]').forEach(tr => {
    tr.addEventListener('click', () => {
      const sym = tr.dataset.sym;
      const det = document.querySelector(`tr.detail[data-det="${sym}"]`);
      if (det) det.style.display = det.style.display === 'none' ? '' : 'none';
    });
  });
}

/* ── window bağları (inline onclick/oninput/onchange için) ── */
Object.assign(window, {
  badge, g05Cipleri, rsiYorum, hacimOranHtml, genislikHtml, mfiYorum, trendHtml,
  squeezeHtml, sparkSVG, reelBistGrafik, reelBistTablo, trRiskHtml, hisseSatir,
  tabloBolum, renderPiyasa, filtrele, csvIndir
});
/* PIYASA_VERI canlı bağ: Object.assign null'ı kopyalar → getter ile bağla */
Object.defineProperty(window, 'PIYASA_VERI', { get: () => PIYASA_VERI, configurable: true });
Object.defineProperty(window, 'durum', { get: () => durum, configurable: true });

/* Portföy + alarmlar ayrı dosyada (portfoy.js); yan etki için import edilir. */
import { alarmKontrol } from './portfoy.js';
export { alarmKontrol };
