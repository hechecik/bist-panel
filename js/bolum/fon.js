/* js/bolum/fon.js — FON bölümü (G06 parça 3)
   renderFon: TEFAS fon risk iştahı, fon getirileri, sektör dağılımı,
   BIST 30 temel analiz. */
import { fmt, ok } from '../core.js';

/* ══════════ FON ══════════ */
const SEKTOR_TR = {'Industrials':'Sanayi','Financial Services':'Finans','Basic Materials':'Hammadde',
  'Consumer Cyclical':'Tüketici','Consumer Defensive':'Temel Tüketim','Technology':'Teknoloji',
  'Communication Services':'İletişim','Energy':'Enerji','Utilities':'Kamu Hizmetleri',
  'Real Estate':'Gayrimenkul','Healthcare':'Sağlık'};
const sekTr = s => SEKTOR_TR[s] || s || '—';

export function renderFon(d) {
  const f = d.fonlar;
  let html = '<h2>🏦 Fonlar & Kurumsal</h2>';

  if (f && f.fonlar && f.fonlar.length) {
    if (f.ozet && f.ozet.fon_sayisi) {
      html += `<h2>📊 Fonların Risk İştahı <span class="cnt">${f.tarih}</span></h2>`;
      html += '<div class="scn">' +
        `<div class="sc"><div class="t">İncelenen Fon</div><div class="o">${f.ozet.fon_sayisi}</div></div>` +
        `<div class="sc"><div class="t">Ort. Hisse Ağırlığı</div><div class="o ${f.ozet.ort_hisse_agirlik >= 50 ? 'up' : 'down'}">%${f.ozet.ort_hisse_agirlik}</div></div>` +
        (f.ozet.max_hisse_agirlik != null ? `<div class="sc"><div class="t">En Riskli Fon</div><div class="o up">%${f.ozet.max_hisse_agirlik}</div></div>` : '') +
        '</div>';
    }
    html += '<h2>📈 Fon Getirileri (TEFAS)</h2><div class="twrap"><table><tr>' +
      '<th>Fon</th><th>Hisse %</th><th>1 Ay</th><th>3 Ay</th><th>6 Ay</th><th>1 Yıl</th></tr><tbody>';
    f.fonlar.forEach(fn => {
      const g = fn.getiri || {};
      const h = x => x == null ? '—' : `<span class="${ok(x)}">${x >= 0 ? '+' : ''}%${x.toFixed(1)}</span>`;
      html += `<tr><td class="sym">${fn.kod}</td><td>%${fn.hisse_agirlik}</td>` +
        `<td>${h(g['1A'])}</td><td>${h(g['3A'])}</td><td>${h(g['6A'])}</td><td>${h(g['1Y'])}</td></tr>`;
    });
    html += '</tbody></table></div>';
    html += '<h2>📋 Fon Dağılımları</h2>';
    f.fonlar.forEach(fn => {
      const renk = fn.hisse_agirlik >= 50 ? 'var(--up)' : 'var(--warn)';
      html += `<div class="ev"><div class="nm"><b>${fn.kod}</b> · ${fn.tarih} · <span style="color:${renk}">Hisse %${fn.hisse_agirlik}</span><br>` +
        `<small style="color:var(--tx2)">${fn.varliklar.map(v=>`${v.sinif} %${v.agirlik}`).join(' · ')}</small></div></div>`;
    });
    html += '<div class="note">' + (f.not || '') + '</div>';
  } else {
    html += '<div class="empty">🏦 TEFAS fon verisi şu an yok — bir sonraki güncellemede</div>';
  }

  if (d.sektorler && d.sektorler.length) {
    html += '<h2>🏭 Sektör Dağılımı <span class="cnt">' + d.sektorler.length + '</span></h2><div class="twrap"><table><tr>' +
      '<th>Sektör</th><th>Hisse</th><th>Ort. Skor</th><th>🟢 AL</th><th>🔴 SAT</th><th>Dağılım</th></tr><tbody>';
    const maxH = Math.max(...d.sektorler.map(x => x.hisse_sayisi));
    d.sektorler.forEach(x => {
      const genislik = Math.round(x.hisse_sayisi / maxH * 100);
      html += `<tr><td class="sym">${sekTr(x.sektor)}</td><td>${x.hisse_sayisi}</td>` +
        `<td class="${ok(x.ort_skor)}">${x.ort_skor > 0 ? '+' : ''}${x.ort_skor}</td>` +
        `<td class="up">${x.al}</td><td class="down">${x.sat}</td>` +
        `<td style="min-width:110px"><div class="bar"><i style="width:${genislik}%;background:var(--accent)"></i></div></td></tr>`;
    });
    html += '</tbody></table></div><div class="note">Sektörler Yahoo Finance resmi sınıflandırmasıdır.</div>';
  }

  if (d.temel_analiz && d.temel_analiz.length) {
    html += '<h2>💎 Temel Analiz — BIST 30 <span class="cnt">değer skoru</span></h2><div class="twrap"><table><tr>' +
      '<th>Hisse</th><th>F/K</th><th>PD/DD</th><th>Temettü</th><th>Skor</th><th>Not</th></tr><tbody>';
    d.temel_analiz.forEach(x => {
      let notlar = [];
      if (x.fk != null && x.fk < 5) notlar.push('F/K çok ucuz');
      else if (x.fk != null && x.fk < 10) notlar.push('F/K ucuz');
      if (x.pddd != null && x.pddd < 1) notlar.push('PD/DD defter altı');
      if (x.temettu != null && x.temettu > 3) notlar.push('Yüksek temettü');
      html += `<tr><td class="sym">${x.sembol}</td>` +
        `<td>${x.fk == null ? '—' : fmt(x.fk)}</td>` +
        `<td>${x.pddd == null ? '—' : fmt(x.pddd)}</td>` +
        `<td>${x.temettu == null ? '—' : '%' + fmt(x.temettu,1)}</td>` +
        `<td style="color:${x.skor >= 3 ? 'var(--up)' : 'var(--warn)'};font-weight:700">+${x.skor}</td>` +
        `<td class="ned">${notlar.join(' · ') || '—'}</td></tr>`;
    });
    html += '</tbody></table></div><div class="note">Değer skoru: F/K&lt;5 (+2), &lt;10 (+1); PD/DD&lt;1 (+2), &lt;1.5 (+1); temettü&gt;%3 (+1).</div>';
  }
  document.getElementById('fon-icerik').innerHTML = html;
}

window.renderFon = renderFon;
