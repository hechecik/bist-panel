import { fmt, yuzde, ok, durum } from '../core.js';
import { badge, sparkSVG, g05Cipleri, rsiYorum, hacimOranHtml, mfiYorum, trendHtml, squeezeHtml } from './piyasa-yardimci.js';

/* ── TABLO ── */
export const KOLONLAR = ['Hisse','Grafik','Fiyat','1A','RS20','Hacim','Skor','Sinyal','Trend','Para','RSI','MFI','Squeeze','S1/R1','SL/Hdf','Neden','📈'];

export function hisseSatir(r, durum) {
  const onceki = durum.detay.has(r.sembol) ? durum.detay.get(r.sembol) : r;
  const bol = (durum.bolunme || []).filter(b => b.sembol === r.sembol);
  const bolNot = bol.length
    ? `<div class="bol"><span>⚙️ bölünme düzeltildi</span>` +
      bol.map(b => `<span>${b.tarih} · oran ${b.oran}</span>`).join('') + `</div>`
    : '';
  let html = `<tr data-sym="${r.sembol}">` +
    `<td class="sym">${r.sembol}${bolNot}${g05Cipleri(r)}</td>` +
    `<td>${sparkSVG(r)}</td>` +
    `<td>${fmt(r.fiyat)}</td>` +
    `<td class="${ok(r.ay_oncesi)}">${r.ay_oncesi == null ? '—' : yuzde(r.ay_oncesi)}</td>` +
    `<td class="${ok(r.RS20)}" title="RS20 — hisse/XU100 oranının 20 günlük değişimi">${r.RS20 == null ? '—' : yuzde(r.RS20)}</td>` +
    `<td title="Hacim oranı — bugünkü hacim / 20 günlük medyan">${hacimOranHtml(r)}</td>` +
    `<td style="color:${r.skor>=3?'var(--up)':r.skor<=-3?'var(--down)':'var(--warn)'};font-weight:700">${r.skor>0?'+':''}${r.skor}</td>` +
    `<td>${badge(r.sinyal)}</td>` +
    `<td>${trendHtml(r)}</td>` +
    `<td>${mfiYorum(r)}</td>` +
    `<td>${rsiYorum(r)}</td>` +
    `<td>${r.mfi == null ? '—' : fmt(r.mfi,0)}</td>` +
    `<td>${squeezeHtml(r)}</td>` +
    `<td>${r.s1 == null ? '—' : `<span style="color:var(--down)">${fmt(r.s1)}</span> / <span style="color:var(--up)">${fmt(r.r1)}</span>`}</td>` +
    `<td>${r.stop == null ? '—' : `${fmt(r.stop)} / ${fmt(r.hedef)}`}</td>` +
    `<td class="ned">${(r.nedenler||[]).slice(0,2).map(n=>'▸ '+n).join('<br>')}</td>` +
    `<td><button class="gbtn" onclick="event.stopPropagation();grafikModal('${r.sembol}')" title="Mum grafiği aç">📈</button></td></tr>`;
  if (onceki) {
    html += `<tr class="detail" data-det="${r.sembol}"><td colspan="${KOLONLAR.length}"><div class="det-ic">` +
      `<div><div class="k">📋 Tüm Nedenler</div><ul>${(r.nedenler||[]).map(n=>`<li>${n}</li>`).join('')}</ul></div>` +
      `<div><div class="k">🎯 Seviyeler</div><ul>` +
      `<li>1. Destek (S1): <b>${r.s1 == null ? '—' : fmt(r.s1)}</b></li>` +
      `<li>1. Direnç (R1): <b>${r.r1 == null ? '—' : fmt(r.r1)}</b></li>` +
      `<li>Stop-loss: <b>${r.stop == null ? '—' : fmt(r.stop)}</b></li>` +
      `<li>Hedef: <b>${r.hedef == null ? '—' : fmt(r.hedef)}</b></li></ul></div>` +
      `<div><div class="k">📅 Veri</div><ul>` +
      `<li>Son bar: <b>${r.tarih || '—'}</b></li>` +
      `<li>1A getiri: <b class="${ok(r.ay_oncesi)}">${r.ay_oncesi == null ? '—' : yuzde(r.ay_oncesi)}</b></li>` +
      `<li>MACD hist: <b>${r.macd_hist == null ? '—' : r.macd_hist}</b></li>` +
      `<li>RS20 (XU100'e göre): <b class="${ok(r.RS20)}">${r.RS20 == null ? '—' : yuzde(r.RS20)}</b></li>` +
      `<li>RS60: <b class="${ok(r.RS60)}">${r.RS60 == null ? '—' : yuzde(r.RS60)}</b></li>` +
      `<li>Hacim oranı (20g medyan): <b>${r.HACIM_ORAN == null ? '—' : fmt(r.HACIM_ORAN,2) + '×'}</b></li>` +
      `<li>VOL20 (günlük getiri std): <b>${r.VOL20 == null ? '—' : '%' + fmt(r.VOL20,2)}</b></li>` +
      `<li>52h zirveye uzaklık: <b>${r.ZIRVE_UZAK == null ? '—' : yuzde(r.ZIRVE_UZAK)}</b></li>` +
      `<li>Trend/ATR: <b>${r.TREND_ATR == null ? '—' : fmt(r.TREND_ATR,2)}</b></li>` +
      `<li>Analiz: <b>${durum.hesapTarihi || '—'}</b></li></ul></div>` +
      `<div><div class="k">🔎 G05 Filtre</div><ul>` +
      `<li>Kilit: <b>${r.kilit || 'yok'}</b></li>` +
      `<li>Likidite (20g): <b>${r.likidite_tl == null ? '—' : fmt(r.likidite_tl/1000000,1) + ' mn ₺'}</b></li>` +
      `<li>Yeni arz: <b>${r.ipo_yeni ? 'evet' + (r.ipo_tarih ? ' · ' + r.ipo_tarih : '') : 'hayır'}</b></li>` +
      `<li>VBTS tedbir: <b>${r.tedbir || 'yok'}</b></li>` +
      `<li>Taban (10g): <b>${r.taban_10g == null ? '—' : r.taban_10g}</b></li>` +
      `<li>Filtre: <b>${r.filtre || '—'}</b>${r.sinyal_ham ? ` <span style="color:var(--tx2)">(ham: ${r.sinyal_ham})</span>` : ''}</li></ul></div>` +
      `</div></td></tr>`;
  }
  return html;
}

export function tabloBolum(baslik, ikon, liste) {
  let html = `<h2>${ikon} ${baslik} <span class="cnt">${liste.length}</span></h2>`;
  if (!liste.length) return html + '<div class="empty">Sonuç yok</div>';
  html += `<div class="twrap"><table><tr>` + KOLONLAR.map(k => `<th class="${k==='Hisse'?'sym':''}">${k}</th>`).join('') + '</tr><tbody>';
  liste.forEach(r => html += hisseSatir(r, durum));
  return html + '</tbody></table></div>';
}
