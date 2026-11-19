/* js/bolum/fon.js — FON bölümü (G06 parça 3)
   renderFon: TEFAS fon risk iştahı, fon getirileri, sektör dağılımı,
   BIST 30 temel analiz. */
import { fmt, ok, alEsc } from '../core.js';

/* ══════════ FON ══════════ */
const SEKTOR_TR = {'Industrials':'Sanayi','Financial Services':'Finans','Basic Materials':'Hammadde',
  'Consumer Cyclical':'Tüketici','Consumer Defensive':'Temel Tüketim','Technology':'Teknoloji',
  'Communication Services':'İletişim','Energy':'Enerji','Utilities':'Kamu Hizmetleri',
  'Real Estate':'Gayrimenkul','Healthcare':'Sağlık'};
const sekTr = s => SEKTOR_TR[s] || s || '—';

export function renderFon(d) {
  const f = d.fonlar;
  let html = '<h2>🏦 Fonlar & Kurumsal</h2>';

  /* ── SENARYO → FON EŞLEŞTİRME (hangi fon neyi kapsar, hangi vadeye uygun) ── */
  if (f && f.senaryolar && f.senaryolar.length) {
    const gx = x => x == null ? '<span class="muted">—</span>'
      : `<span class="${ok(x)}">${x >= 0 ? '+' : '−'}%${Math.abs(x).toFixed(1).replace('.', ',')}</span>`;
    html += `<h2>🎯 Senaryoya Göre Fon Seçimi <span class="cnt">${f.tarih || ''}` +
      `${f.bayat ? ' <span class="warn">bayat</span>' : ''}</span></h2>` +
      '<div class="altnot">"1 ay içinde lazım", "altın", "BIST 30", "yabancı teknoloji" gibi ' +
      'senaryoya aday fonlar. Her senaryo kendi vadesindeki getiriye göre sıralı; ' +
      'listenin altındaki eşiğin altında kalan fonlar sıralamaya alınmaz.</div>';
    f.senaryolar.forEach(s => {
      const siralamaAd = { '1A': '1 ay', '3A': '3 ay', '6A': '6 ay', 'YBB': 'yıl başı', '1Y': '1 yıl' }[s.sirala] || s.sirala;
      html += `<div class="ev" style="display:block">` +
        `<div class="nm" style="display:flex;gap:8px;align-items:baseline;flex-wrap:wrap">` +
        `<b>${s.ikon || ''} ${alEsc(s.ad)}</b>` +
        `<span class="cnt">${alEsc(s.vade)} · sıra: ${siralamaAd}</span></div>` +
        `<div style="color:var(--tx2);font-size:12px;margin:2px 0 6px">` +
        `Kapsam: ${alEsc(s.kapsam)}</div>` +
        '<div class="twrap"><table><tr><th>Kod</th><th>Fon</th><th>Büyüklük</th>' +
        '<th>1 Ay</th><th>3 Ay</th><th>6 Ay</th><th>YBB</th><th>1 Yıl</th></tr><tbody>';
      s.fonlar.forEach((x, i) => {
        const g = x.getiri || {};
        const b = x.boyut_m >= 1000 ? (x.boyut_m / 1000).toFixed(1) + ' mlr' : Math.round(x.boyut_m) + ' mn';
        html += `<tr><td class="sym">${i === 0 ? '★ ' : ''}${x.kod}</td>` +
          `<td class="ned">${alEsc(x.ad || '')}</td><td>${b}</td>` +
          `<td>${gx(g['1A'])}</td><td>${gx(g['3A'])}</td><td>${gx(g['6A'])}</td>` +
          `<td>${gx(g['YTD'])}</td><td>${gx(g['1Y'])}</td></tr>`;
      });
      html += '</tbody></table></div>' +
        `<div class="note">${alEsc(s.not || '')}` +
        (s.buyukluk_disi && s.buyukluk_disi.length
          ? ` <b>${s.esik_mn} mn TL altı olduğu için listeye alınmadı:</b> ${s.buyukluk_disi.join(', ')}.`
          : '') +
        '</div></div>';
    });
  }

  /* ── Kategori bazlı top-10 performans (TEFAS, 1 aylık getiriye göre sıralı) ── */
  if (f && f.kategoriler && f.kategoriler.length) {
    const g = x => x == null ? '—' : `<span class="${ok(x)}">${x >= 0 ? '+' : '−'}%${Math.abs(x).toFixed(2).replace('.', ',')}</span>`;
    html += `<h2>🏆 Kategori Bazlı Fon Performansı <span class="cnt">${f.tarih || ''}` +
      `${f.bayat ? ' <span class="warn">bayat</span>' : ''}</span></h2>` +
      `<div class="altnot">${f.taranan || 0} fon tarandı · ${f.kategoriler.length} kategori · ` +
      `sıralama: 1 aylık getiri</div>`;
    f.kategoriler.forEach(k => {
      html += `<h3 class="fkat">${k.ad} <span class="cnt">${k.fon_sayisi} fon · top ${k.top.length}</span></h3>` +
        '<div class="twrap"><table><tr><th>#</th><th>Kod</th><th>Fon Adı</th><th>Büyüklük</th>' +
        '<th>1 Ay</th><th>3 Ay</th><th>6 Ay</th><th>YBB</th><th>1 Yıl</th></tr><tbody>';
      k.top.forEach((x, i) => {
        const gg = x.getiri || {};
        html += `<tr><td>${i + 1}</td><td class="sym">${x.kod}</td>` +
          `<td class="ned">${alEsc(x.ad || '')}</td>` +
          `<td>${x.boyut_m >= 1000 ? (x.boyut_m / 1000).toFixed(1) + ' mlr' : Math.round(x.boyut_m) + ' mn'}</td>` +
          `<td>${g(gg['1A'])}</td><td>${g(gg['3A'])}</td><td>${g(gg['6A'])}</td>` +
          `<td>${g(gg['YTD'])}</td><td>${g(gg['1Y'])}</td></tr>`;
      });
      html += '</tbody></table></div>';
    });
    html += `<div class="note">${alEsc(f.siralama_notu || '')}</div>`;
  }

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
