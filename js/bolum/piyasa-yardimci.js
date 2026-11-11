import { fmt, yuzde, ok } from '../core.js';

/* ── piyasa bölümü yardımcıları (rozet, çipler, yorumlar, sparkline) ── */
export function badge(s) {
  const m = {'AL':'b-AL','DİKKAT_AL':'b-DİKKAT_AL','TUT':'b-TUT','DİKKAT_SAT':'b-DİKKAT_SAT','SAT':'b-SAT',
             'IZLE':'b-IZLE','RISKLI':'b-RISKLI'};
  return `<span class="badge ${m[s]||'b-TUT'}">${s}</span>`;
}

/* ══════════ G05 — BIST filtreleri ══════════ */
export function g05Cipleri(r) {
  const c = [];
  if (r.kilit === 'TAVAN') c.push('<span class="tavan" title="Kapanış gün yükseğinde, +%9,5 ve üzeri">🔒 TAVAN</span>');
  if (r.kilit === 'TABAN') c.push('<span class="taban" title="Kapanış gün düşüğünde, −%9,5 ve altı">🔒 TABAN</span>');
  if (r.ipo_yeni) c.push(`<span class="ipo" title="Son 60 iş günü içinde işlem görmeye başladı${r.ipo_tarih ? ' · ilk bar ' + r.ipo_tarih : ''}">🆕 YENİ ARZ</span>`);
  if (r.riskli) c.push(`<span class="risk" title="${r.riskli}">⛔ RİSKLİ — ${r.riskli}</span>`);
  if (r.tedbir) c.push(`<span class="tedbir" title="VBTS tedbiri">⛔ TEDBİR: ${r.tedbir}</span>`);
  if (r.likidite_tl != null && r.likidite_tl < 50000000)
    c.push(`<span class="dusuk" title="20 günlük ort. TL hacmi eşiğin altında (50 mn ₺)">💧 ${fmt(r.likidite_tl/1000000,1)} mn ₺</span>`);
  if (r.filtre) c.push(`<span class="tedbir" title="Ham sinyal: ${r.sinyal_ham || '—'}">⤵ ${r.filtre}</span>`);
  return c.length ? `<div class="g05">${c.join('')}</div>` : '';
}

/* ── YORUMLAR ── */
export function rsiYorum(r) {
  if (r.rsi == null) return '';
  if (r.rsi < 30) return `<span style="color:var(--info)">${fmt(r.rsi,0)} aşırı satım</span>`;
  if (r.rsi > 70) return `<span style="color:var(--down)">${fmt(r.rsi,0)} aşırı alım</span>`;
  if (r.rsi >= 55) return `<span style="color:var(--up)">${fmt(r.rsi,0)} güçlü</span>`;
  if (r.rsi >= 45) return `<span style="color:var(--tx)">${fmt(r.rsi,0)} nötr</span>`;
  return `<span style="color:var(--warn)">${fmt(r.rsi,0)} zayıf</span>`;
}
/* G09 — gölge mod göstergeleri (skor/sinyale girmez, sadece gösterim) */
export function hacimOranHtml(r) {
  if (r.HACIM_ORAN == null) return '—';
  const v = r.HACIM_ORAN;
  const renk = v >= 2 ? 'var(--up)' : (v <= 0.6 ? 'var(--tx2)' : 'var(--tx)');
  return `<span style="color:${renk}" title="${v >= 1.5 ? 'Ortalamanın belirgin üzerinde hacim' : v <= 0.6 ? 'Ortalamanın altında hacim' : 'Normal hacim'}">${fmt(v,2)}×</span>`;
}
/* G09 — piyasa genişliği kartı (piyasa sekmesi) */
export function genislikHtml(g) {
  if (!g || g.durum === 'veri yok' || g.ma50_ustu_yuzde == null) return '';
  const renk = g.ma50_ustu_yuzde >= 60 ? 'var(--up)' : (g.ma50_ustu_yuzde <= 40 ? 'var(--down)' : 'var(--warn)');
  return `<h2>📐 Piyasa Genişliği <span class="cnt">${g.hisse || ''} hisse · ${g.tarih || ''}</span></h2>` +
    `<div class="cards">` +
    `<div class="card"><div class="t">MA50 üstü</div><div class="v" style="color:${renk}">%${fmt(g.ma50_ustu_yuzde,1)}</div><div class="t">${g.ma50_ustu == null ? '' : g.ma50_ustu + ' hisse'}</div></div>` +
    `<div class="card"><div class="t">Yükselen</div><div class="v up">${g.yukselen == null ? '—' : g.yukselen}</div></div>` +
    `<div class="card"><div class="t">Düşen</div><div class="v down">${g.dusen == null ? '—' : g.dusen}</div></div>` +
    `<div class="card"><div class="t">52h zirve</div><div class="v up">${g.yeni_zirve_52h == null ? '—' : g.yeni_zirve_52h}</div></div>` +
    `<div class="card"><div class="t">52h dip</div><div class="v down">${g.yeni_dip_52h == null ? '—' : g.yeni_dip_52h}</div></div>` +
    `</div>`;
}
export function mfiYorum(r) {
  if (r.mfi == null) return '—';
  const renk = r.para === 'GİRİŞ' ? 'var(--up)' : (r.para === 'ÇIKIŞ' ? 'var(--down)' : 'var(--tx)');
  return `<span style="color:${renk}">${fmt(r.mfi,0)} ${r.para || ''}</span>`;
}
export function trendHtml(r) {
  if (r.trend === 'YUKARI') return '▲ <span class="up">YUKARI</span>';
  if (r.trend === 'AŞAĞI') return '▼ <span class="down">AŞAĞI</span>';
  return '▶ <span style="color:var(--tx2)">YATAY</span>';
}
export function squeezeHtml(r) {
  const s = (r.squeeze || '').toUpperCase();
  if (s.includes('YUKARI')) return '🚀 <span class="up">KIRILIM ↑</span>';
  if (s.includes('AŞAĞI')) return '🕳️ <span class="down">KIRILIM ↓</span>';
  if (s.includes('SIKIŞMA')) return '🧲 <span style="color:var(--warn)">SIKIŞMA</span>';
  return '—';
}
export function sparkSVG(r) {
  if (!r.spark || r.spark.length < 2) return '—';
  const v = r.spark;
  const min = Math.min(...v), max = Math.max(...v);
  const W = 84, H = 26, span = (max - min) || 1;
  const pts = v.map((x, i) => `${(i/(v.length-1)*W).toFixed(1)},${(H-2-((x-min)/span)*(H-4)).toFixed(1)}`).join(' ');
  const renk = v[v.length-1] >= v[0] ? 'var(--up)' : 'var(--down)';
  return `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><polyline points="${pts}" fill="none" stroke="${renk}" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/></svg>`;
}

/* ── G13 — reel BIST (TL / USD / gram altın, 100'e normalize) ── */
function reelBistGrafik(rb) {
  const seriler = [
    { ad: 'TL', renk: 'var(--tx)', anahtar: 'tl', kisa: 'TL' },
    { ad: 'USD', renk: 'var(--up)', anahtar: 'usd', kisa: 'USD' },
    { ad: 'Gram altın', renk: 'var(--warn)', anahtar: 'altin', kisa: 'ALTIN' },
  ].filter(s => (rb[s.anahtar] || []).length > 1);
  if (!seriler.length) return '';
  const n = seriler[0] ? rb[seriler[0].anahtar].length : 0;
  // ortak gün kümesi: tüm seriler aynı uzunlukta (tarihe göre hizalanmış)
  // her seri dönem başına göre 100'e normalize edilir → üç çizgi aynı ölçekte okunur
  const norm = {};
  seriler.forEach(s => { const v0 = rb[s.anahtar][0][1]; norm[s.anahtar] = rb[s.anahtar].map(p => p[1] / v0 * 100); });
  const W = 720, H = 220, PL = 6, PR = 6, PT = 8, PB = 8;
  const hepsi = seriler.flatMap(s => norm[s.anahtar]);
  const min = Math.min(...hepsi), max = Math.max(...hepsi);
  const span = (max - min) || 1;
  const X = i => PL + (i / Math.max(1, n - 1)) * (W - PL - PR);
  const Y = v => PT + (1 - (v - min) / span) * (H - PT - PB);
  let cizgi = '';
  seriler.forEach(s => {
    const v = norm[s.anahtar];
    const pts = v.map((x, i) => `${X(i).toFixed(1)},${Y(x).toFixed(1)}`).join(' ');
    cizgi += `<polyline points="${pts}" fill="none" stroke="${s.renk}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>`;
    cizgi += `<circle cx="${X(v.length - 1).toFixed(1)}" cy="${Y(v[v.length - 1]).toFixed(1)}" r="2.6" fill="${s.renk}"/>`;
  });
  const yuzCizgi = Y(100);
  const lejant = seriler.map(s => {
    const deg = norm[s.anahtar][n - 1] - 100;
    return `<span style="color:${s.renk}">■ ${s.kisa} ${deg >= 0 ? '+' : ''}${fmt(deg, 1)}%</span>`;
  }).join(' · ');
  return `<h2>💵 Reel BIST — XU100 (100'e normalize) <span class="cnt">${rb.bas || ''} → ${rb.son || ''} · ${rb.hizalama ? rb.hizalama.eslesen_gun : n} gün</span></h2>` +
    `<div class="tcmb" style="padding:10px 12px">` +
    `<div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:4px">` +
    `<span style="font-size:11px">${lejant}</span>` +
    `<span style="font-size:10px;color:var(--tx2)">eşik: ${fmt(min, 1)} – ${fmt(max, 1)} (100 = dönem başı)</span></div>` +
    `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="width:100%;height:150px;display:block">` +
    (100 >= min && 100 <= max ? `<line x1="${PL}" y1="${yuzCizgi.toFixed(1)}" x2="${W - PR}" y2="${yuzCizgi.toFixed(1)}" stroke="var(--bd)" stroke-width="1" stroke-dasharray="4 4"/>` : '') +
    cizgi + `</svg></div>`;
}

function reelBistTablo(rb) {
  const g = rb.getiriler || {};
  const d = g.donemler || {};
  if (!Object.keys(d).length) return '';
  const ADLAR = { '1h': '1 hafta', '1a': '1 ay', '3a': '3 ay', '1y': '1 yıl', 'ybb': 'YBB' };
  const hucre = v => v == null ? '<span style="color:var(--tx2)">veri yok</span>'
    : `<span class="${ok(v)}">${v >= 0 ? '+' : ''}${fmt(v, 2)}%</span>`;
  let satir = '';
  ['1h', '1a', '3a', '1y', 'ybb'].forEach(kod => {
    const r = d[kod];
    if (!r) return;
    satir += `<tr><td><b>${ADLAR[kod]}</b></td><td>${hucre(r.tl)}</td><td>${hucre(r.usd)}</td><td>${hucre(r.altin)}</td>` +
      `<td style="color:var(--tx2)">${r.bas_tarih ? r.bas_tarih + ' → ' + (g.son_tarih || '') : (r.durum || '')}</td></tr>`;
  });
  const tut = (g.tutarlilik || []).filter(t => t.ok === true).length;
  const tutToplam = (g.tutarlilik || []).filter(t => t.ok !== undefined).length;
  return `<h2>📊 Reel Getiri Tablosu <span class="cnt">XU100 · TL / USD / gram altın</span></h2>` +
    `<div class="twrap"><table style="min-width:560px"><tr><th>Dönem</th><th>TL</th><th>USD</th><th>Gram altın</th><th>Tarih aralığı</th></tr>` +
    `<tbody>${satir}</tbody></table></div>` +
    `<div class="note">Pencereler iş günü (1h=5, 1a=21, 3a=63, 1y=252 bar) · seriler TARİHE göre hizalandı · ` +
    `Tutarlılık (1+TL)/(1+USDTRY)−1 ≈ USD: ${tut}/${tutToplam} dönem ±%0,1 içinde` +
    (g.son_tarih ? ` · son bar ${g.son_tarih}` : '') + `.</div>`;
}

/* ── G13 — Türkiye risk kartı (reel faiz, tahvil, PPK) ── */
function trRiskHtml(t) {
  if (!t || t.durum === 'veri yok') return '';
  const rf = t.reel_faiz || {};
  const pol = t.politika || {};
  const tf = t.tufe || {};
  const tv = t.tahvil || {};
  const pp = t.ppk || {};
  const sn = pp.sonraki || {};
  const deger = (v, ek) => v == null ? '<span style="color:var(--tx2)">veri yok</span>' : `<b>${v}${ek || ''}</b>`;
  let s = `<h2>🇹🇷 Türkiye Risk Kartı <span class="cnt">${t.uretildi ? 'üretim ' + t.uretildi.slice(0, 16).replace('T', ' ') + ' UTC' : ''}</span></h2>`;
  s += `<div class="cards">`;
  s += `<div class="card"><div class="t">Reel faiz</div><div class="v ${rf.deger == null ? '' : ok(rf.deger)}">` +
    `${rf.deger == null ? '—' : (rf.deger >= 0 ? '+' : '') + fmt(rf.deger, 2) + ' puan'}</div>` +
    `<div class="t">${pol.faiz == null ? 'politika faizi yok' : '%' + fmt(pol.faiz, 2)} − ${tf.yillik == null ? 'TÜFE yok' : '%' + fmt(tf.yillik, 2)}</div></div>`;
  s += `<div class="card"><div class="t">Politika faizi</div><div class="v">${pol.faiz == null ? '—' : '%' + fmt(pol.faiz, 2)}</div>` +
    `<div class="t">${pol.karar ? 'karar ' + pol.karar : (pol.uygulama || '')}</div></div>`;
  s += `<div class="card"><div class="t">TÜFE yıllık</div><div class="v">${tf.yillik == null ? '—' : '%' + fmt(tf.yillik, 2)}</div>` +
    `<div class="t">${tf.tarih || ''}</div></div>`;
  s += `<div class="card"><div class="t">TR 2Y / 10Y</div><div class="v" style="font-size:17px">${tv['2Y'] == null ? '—' : '%' + fmt(tv['2Y'], 2)} / ${tv['10Y'] == null ? '—' : '%' + fmt(tv['10Y'], 2)}</div>` +
    `<div class="t">${tv.goster === 'tahvil_durum' ? alEsc(tv.metin || 'tahvil durumu yok') : (tv.durum || '')}</div></div>`;
  s += `<div class="card"><div class="t">Sonraki PPK</div><div class="v">${sn.tarih || '—'}</div>` +
    `<div class="t">${sn.kalan_gun == null ? (pp.not || '') : sn.kalan_gun + ' gün kaldı'}</div></div>`;
  s += `</div>`;
  if (rf.yorum) s += `<div class="tcmb" style="margin-top:8px">${rf.yorum}${rf.formul ? ` <span style="color:var(--tx2)">(${rf.formul})</span>` : ''}</div>`;
  const ek = [];
  if (pp.gelecek && pp.gelecek.length > 1) ek.push(`PPK takvimi: ${pp.gelecek.map(x => alEsc(x)).join(' · ')}`);
  if ((t.rezerv || {}).metin) ek.push(`Rezervler: ${alEsc(t.rezerv.metin)}`);
  if ((t.cds || {}).metin) ek.push(alEsc(t.cds.metin));
  if (pp.uyari) ek.push(alEsc(pp.uyari));
  if (ek.length) s += `<div class="note">${ek.join('<br>')}</div>`;
  return s;
}

/* ── VERİ TAZELİĞİ ── */
/* ── BAYAT VERİ BANDI (G01) ──
   Hisse verisi hafta içi 1 iş gününden eskiyse, altın verisi 2 saatten eskiyse
   sayfanın üstünde kırmızı bant gösterilir. */
