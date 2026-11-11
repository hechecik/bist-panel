/* js/bolum/getiri.js — SABİT GETİRİ bölümü (G06 parça 3)
   getiriYukle: devlet tahvili + eurobond kotasyonları (data/getiri.json). */
import { fmt, ok } from '../core.js';

/* ══════════ SABİT GETİRİ (devlet tahvili + eurobond) ══════════ */
export async function getiriYukle() {
  const el = document.getElementById('getiri-blok');
  if (!el) return;
  try {
    const g = await (await fetch('data/getiri.json?v=' + Date.now())).json();
    const rf = g.risk_free != null ? 'Risksiz getiri (10Y): <b>%' + fmt(g.risk_free) + '</b> · ' : '';
    let h = '<h2>💵 Sabit Getiri — Devlet Tahvili & Eurobond <span class="cnt">' +
      (g.tahvil ? g.tahvil.length : 0) + ' tahvil · ' + (g.eurobond ? g.eurobond.length : 0) + ' eurobond</span></h2>';

    if (g.tahvil && g.tahvil.length) {
      h += '<div class="scn">';
      g.tahvil.forEach(t => {
        h += `<div class="sc"><div class="t">${t.ad || t.vade}</div>` +
          `<div class="o">%${fmt(t.getiri)}</div>` +
          `<div class="m">${t.vade} · <span class="${ok(t.degisim)}">${t.degisim >= 0 ? '+' : ''}${fmt(t.degisim, 3)}</span></div></div>`;
      });
      h += '</div>';
    } else {
      const sebep = g.tahvil_durum || 'sebep yazılmadı';
      h += '<div class="empty">⚠️ Tahvil verisi alınamadı — <b>' + sebep + '</b></div>';
    }

    if (g.eurobond && g.eurobond.length) {
      h += '<h2>🌍 Eurobond <span class="cnt">' + g.eurobond.length + ' kıymet · Ziraat kotasyonu</span></h2>' +
        '<div class="twrap"><table><tr><th>Vade</th><th>Kalan Gün</th><th>Döviz</th><th>Alış Fiyatı</th><th>Alış Oranı</th><th>Satış Fiyatı</th><th>Satış Oranı</th></tr><tbody>';
      g.eurobond.forEach(e => {
        h += `<tr><td class="sym">${e.vade || ''}</td><td>${e.kalan_gun == null ? '—' : e.kalan_gun}</td><td>${e.para || ''}</td>` +
          `<td>${e.alis_fiyat == null ? '—' : fmt(e.alis_fiyat, 3)}</td><td class="up">${e.alis_oran == null ? '—' : '%' + fmt(e.alis_oran)}</td>` +
          `<td>${e.satis_fiyat == null ? '—' : fmt(e.satis_fiyat, 3)}</td><td class="down">${e.satis_oran == null ? '—' : '%' + fmt(e.satis_oran)}</td></tr>`;
      });
      h += '</tbody></table></div>' +
        '<div class="note">' + rf + 'Alış = bankanın <b>sizden</b> alacağı (siz satarken), Satış = bankanın <b>size</b> satacağı (siz alırken). Kaynak: Ziraat Bank eurobond kotasyonu + doviz.com tahvil. Yatırım tavsiyesi değildir.</div>';
    } else {
      h += '<div class="note">' + rf + 'Eurobond kotasyonu şu an alınamadı.</div>';
    }
    el.innerHTML = h;
  } catch (e) {
    el.innerHTML = '<h2>💵 Sabit Getiri</h2><div class="empty">Getiri verisi yüklenemedi: ' + (e && e.message ? e.message : e) + '</div>';
  }
}

window.getiriYukle = getiriYukle;
