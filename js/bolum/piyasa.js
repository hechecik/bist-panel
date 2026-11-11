/* js/bolum/piyasa.js — PİYASA bölümü (G06 parça 2)
   Taşınanlar: biçimlendirme/rozet yardımcıları, tablo satırı üretimi (hisseSatir,
   tabloBolum, KOLONLAR, durum), renderPiyasa ve alt bileşenleri (genişlik, reel
   BIST grafiği/tablosu, TR risk), filtre + CSV, portföy ve fiyat alarmları.
   Davranış birebir eski main.js ile aynı; window bağları dosya sonunda. */
import { fmt, yuzde, ok, tazelik, alEsc, pfOk, pfRenk } from '../core.js';

export function badge(s) {
  const m = {'AL':'b-AL','DİKKAT_AL':'b-DİKKAT_AL','TUT':'b-TUT','DİKKAT_SAT':'b-DİKKAT_SAT','SAT':'b-SAT',
             'IZLE':'b-IZLE','RISKLI':'b-RISKLI'};
  return `<span class="badge ${m[s]||'b-TUT'}">${s}</span>`;
}

/* ══════════ G05 — BIST filtreleri ══════════ */
function g05Cipleri(r) {
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
function rsiYorum(r) {
  if (r.rsi == null) return '';
  if (r.rsi < 30) return `<span style="color:var(--info)">${fmt(r.rsi,0)} aşırı satım</span>`;
  if (r.rsi > 70) return `<span style="color:var(--down)">${fmt(r.rsi,0)} aşırı alım</span>`;
  if (r.rsi >= 55) return `<span style="color:var(--up)">${fmt(r.rsi,0)} güçlü</span>`;
  if (r.rsi >= 45) return `<span style="color:var(--tx)">${fmt(r.rsi,0)} nötr</span>`;
  return `<span style="color:var(--warn)">${fmt(r.rsi,0)} zayıf</span>`;
}
/* G09 — gölge mod göstergeleri (skor/sinyale girmez, sadece gösterim) */
function hacimOranHtml(r) {
  if (r.HACIM_ORAN == null) return '—';
  const v = r.HACIM_ORAN;
  const renk = v >= 2 ? 'var(--up)' : (v <= 0.6 ? 'var(--tx2)' : 'var(--tx)');
  return `<span style="color:${renk}" title="${v >= 1.5 ? 'Ortalamanın belirgin üzerinde hacim' : v <= 0.6 ? 'Ortalamanın altında hacim' : 'Normal hacim'}">${fmt(v,2)}×</span>`;
}
/* G09 — piyasa genişliği kartı (piyasa sekmesi) */
function genislikHtml(g) {
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
function mfiYorum(r) {
  if (r.mfi == null) return '—';
  const renk = r.para === 'GİRİŞ' ? 'var(--up)' : (r.para === 'ÇIKIŞ' ? 'var(--down)' : 'var(--tx)');
  return `<span style="color:${renk}">${fmt(r.mfi,0)} ${r.para || ''}</span>`;
}
function trendHtml(r) {
  if (r.trend === 'YUKARI') return '▲ <span class="up">YUKARI</span>';
  if (r.trend === 'AŞAĞI') return '▼ <span class="down">AŞAĞI</span>';
  return '▶ <span style="color:var(--tx2)">YATAY</span>';
}
function squeezeHtml(r) {
  const s = (r.squeeze || '').toUpperCase();
  if (s.includes('YUKARI')) return '🚀 <span class="up">KIRILIM ↑</span>';
  if (s.includes('AŞAĞI')) return '🕳️ <span class="down">KIRILIM ↓</span>';
  if (s.includes('SIKIŞMA')) return '🧲 <span style="color:var(--warn)">SIKIŞMA</span>';
  return '—';
}
function sparkSVG(r) {
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
/* ── TABLO ── */
const KOLONLAR = ['Hisse','Grafik','Fiyat','1A','RS20','Hacim','Skor','Sinyal','Trend','Para','RSI','MFI','Squeeze','S1/R1','SL/Hdf','Neden','📈'];

function hisseSatir(r, durum) {
  const onceki = durum.detay.get(r.sembol);
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

export let durum = { detay: new Map(), hesapTarihi: '', bolunme: [] };

function tabloBolum(baslik, ikon, liste) {
  let html = `<h2>${ikon} ${baslik} <span class="cnt">${liste.length}</span></h2>`;
  if (!liste.length) return html + '<div class="empty">Sonuç yok</div>';
  html += `<div class="twrap"><table><tr>` + KOLONLAR.map(k => `<th class="${k==='Hisse'?'sym':''}">${k}</th>`).join('') + '</tr><tbody>';
  liste.forEach(r => html += hisseSatir(r, durum));
  return html + '</tbody></table></div>';
}

/* ══════════ PİYASA ══════════ */
let PIYASA_VERI = null;
export function renderPiyasa(d) {
  PIYASA_VERI = d;
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

/* ══════════ FİLTRE ══════════ */
function filtrele() {
  const q = (document.getElementById('arama').value || '').toUpperCase().trim();
  const fs = document.getElementById('fSinyal').value;
  const ft = document.getElementById('fTrend').value;
  const fq = document.getElementById('fSqueeze').value;
  document.querySelectorAll('#sec-piyasa tbody tr[data-sym]').forEach(tr => {
    const sym = tr.dataset.sym;
    const r = PIYASA_VERI && [...(PIYASA_VERI.sinyaller.al||[]), ...(PIYASA_VERI.sinyaller.tut||[]), ...(PIYASA_VERI.sinyaller.sat||[]), ...(PIYASA_VERI.sinyaller.izle||[]), ...(PIYASA_VERI.sinyaller.riskli||[])].find(x => x.sembol === sym);
    if (!r) return;
    const okS = !fs || r.sinyal === fs;
    const okT = !ft || r.trend === ft;
    const okQ = !fq || (fq === 'SIKIŞMA' ? (r.squeeze||'').toUpperCase().includes('SIKIŞMA') : (r.squeeze||'').toUpperCase().includes('KIRILIM'));
    const okA = !q || sym.includes(q);
    tr.style.display = (okS && okT && okQ && okA) ? '' : 'none';
    const det = document.querySelector(`tr.detail[data-det="${sym}"]`);
    if (det) det.style.display = 'none';
  });
}

/* ══════════ CSV ══════════ */
function csvIndir() {
  const d = PIYASA_VERI; if (!d) return;
  const satirlar = [...(d.sinyaller.al||[]), ...(d.sinyaller.tut||[]), ...(d.sinyaller.sat||[]), ...(d.sinyaller.izle||[]), ...(d.sinyaller.riskli||[])];
  const baslik = 'Hisse,Fiyat,1A%,RS20,RS60,HacimOran,VOL20,ZirveUzak,TrendATR,Skor,Sinyal,Trend,Para,RSI,MFI,Squeeze,S1,R1,Stop,Hedef,Kilit,IpoYeni,Riskli,LikiditeTL,Filtre';
  const csv = [baslik, ...satirlar.map(r =>
    [r.sembol, r.fiyat, r.ay_oncesi ?? '', r.RS20 ?? '', r.RS60 ?? '', r.HACIM_ORAN ?? '', r.VOL20 ?? '',
     r.ZIRVE_UZAK ?? '', r.TREND_ATR ?? '', r.skor, r.sinyal, r.trend, r.para, r.rsi, r.mfi,
     r.squeeze, r.s1 ?? '', r.r1 ?? '', r.stop ?? '', r.hedef ?? '',
     r.kilit ?? '', r.ipo_yeni ? 'EVET' : '', r.riskli ?? '',
     r.likidite_tl == null ? '' : Math.round(r.likidite_tl), r.filtre ?? ''].join(','))].join('\n');
  const blob = new Blob(['\ufeff' + csv], {type:'text/csv;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'bist-panel-' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
}

/* ══════════ PORTFÖY + ALARMLAR (3+6) ══════════ */
function portfoyOku() { try { return JSON.parse(localStorage.getItem('bist_panel_portfoy') || '{}'); } catch(e) { return {}; } }
function portfoyKaydet(p) { localStorage.setItem('bist_panel_portfoy', JSON.stringify(p)); }
function fiyatBul(sym) {
  if (!PIYASA_VERI) return null;
  const hepsi = [...(PIYASA_VERI.sinyaller.al||[]), ...(PIYASA_VERI.sinyaller.tut||[]), ...(PIYASA_VERI.sinyaller.sat||[])];
  const r = hepsi.find(x => x.sembol === sym);
  return r ? r.fiyat : null;
}
function bildirimIzni() {
  if (!('Notification' in window)) return alert('Bu tarayıcı bildirim desteklemiyor');
  Notification.requestPermission().then(p => {
    const el = document.getElementById('bildirimDurum');
    if (el) el.textContent = p === 'granted' ? '✅ Bildirim açık' : '⛔ Bildirim kapalı';
  });
}
function bildirim(ad, mesaj) {
  if ('Notification' in window && Notification.permission === 'granted' && !document.hidden) {
    try {
      new Notification(ad, { body: mesaj, icon: 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📈</text></svg>' });
    } catch(e) {}
  }
}
function portfoyHtml() {
  const p = portfoyOku();
  const semboller = Object.keys(p);
  let toplamMaliyet = 0, toplamDeger = 0, toplamKar = 0;
  let satirlar = '';
  semboller.forEach(sym => {
    const k = p[sym];
    const adet = k.adet, maliyet = k.maliyet;
    const fiyat = fiyatBul(sym);
    toplamMaliyet += adet * maliyet;
    if (fiyat) { toplamDeger += adet * fiyat; toplamKar += (fiyat - maliyet) * adet; }
    const kar = fiyat ? (fiyat - maliyet) * adet : null;
    const alarm = (k.hedef || k.stop)
      ? `<span style="font-size:10px;color:var(--tx2)">🎯${k.hedef ? fmt(k.hedef) : '—'} 🛑${k.stop ? fmt(k.stop) : '—'}</span>`
      : '';
    satirlar += `<div class="pf-row"><span class="sym">${sym}</span>` +
      `<span>${adet} adet @ ${fmt(maliyet)}</span>` +
      `<span>Güncel: <b>${fiyat ? fmt(fiyat) : '—'}</b></span>` +
      `<span class="${ok(kar)}">${kar == null ? '—' : (kar >= 0 ? '+' : '') + fmt(kar,0) + ' TL'}</span>` +
      alarm +
      ((k.hedef || k.stop) ? `<button class="sifirla" onclick="alarmSifirla('${sym}')" title="Alarmı sıfırla">↺</button>` : '') +
      `<button class="sil" onclick="portfoySil('${sym}')">✕</button></div>`;
  });
  const kar = toplamKar;
  const bd = ('Notification' in window) ? (Notification.permission === 'granted' ? '✅ Bildirim açık' : '⛔ Kapalı') : '—';
  return `<div class="portfoy"><div class="top">💼 <b>Portföyüm</b>` +
    (semboller.length ? `<span class="o ${ok(kar)}">${kar >= 0 ? '+' : ''}${fmt(kar,0)} TL</span>` +
      `<span style="color:var(--tx2);font-size:10.5px">maliyet ${fmt(toplamMaliyet,0)} · değer ${fmt(toplamDeger,0)}</span>` : '') +
    `<button class="btn" style="margin-left:auto;padding:5px 10px;font-size:11px" onclick="bildirimIzni()">🔔 <span id="bildirimDurum">${bd}</span></button></div>` +
    (semboller.length ? satirlar : '<div class="empty" style="padding:6px 0">Portföy boş — aşağıdan hisse ekle</div>') +
    `<div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap">` +
    `<input id="pfSym" placeholder="HISSE" style="width:76px" maxlength="10">` +
    `<input id="pfAdet" type="number" placeholder="Adet" style="width:64px" min="1">` +
    `<input id="pfMaliyet" type="number" placeholder="Maliyet TL" style="width:92px" min="0" step="0.01">` +
    `<input id="pfHedef" type="number" placeholder="🎯 Hedef" style="width:80px" min="0" step="0.01">` +
    `<input id="pfStop" type="number" placeholder="🛑 Stop" style="width:80px" min="0" step="0.01">` +
    `<button class="btn" onclick="portfoyEkle()">＋ Ekle</button></div>` +
    `<div class="note">Hedef/stop girersen eşik aşıldığında tarayıcı bildirimi alırsın (sayfa açıkken 15 dk'da bir kontrol). Sadece bu cihazda saklanır.</div></div>`;
}
function portfoyEkle() {
  const sym = (document.getElementById('pfSym').value || '').toUpperCase().trim();
  const adet = parseFloat(document.getElementById('pfAdet').value);
  const maliyet = parseFloat(document.getElementById('pfMaliyet').value);
  const hedef = parseFloat(document.getElementById('pfHedef').value) || null;
  const stop = parseFloat(document.getElementById('pfStop').value) || null;
  if (!sym || !adet || !maliyet) return;
  const p = portfoyOku();
  p[sym] = { adet, maliyet, hedef, stop, tetik_hedef: false, tetik_stop: false };
  portfoyKaydet(p);
  renderPiyasa(PIYASA_VERI);
}
function portfoySil(sym) {
  const p = portfoyOku();
  delete p[sym];
  portfoyKaydet(p);
  renderPiyasa(PIYASA_VERI);
}
function alarmSifirla(sym) {
  const p = portfoyOku();
  if (p[sym]) { p[sym].tetik_hedef = false; p[sym].tetik_stop = false; }
  portfoyKaydet(p);
  renderPiyasa(PIYASA_VERI);
}
export function alarmKontrol() {
  if (!PIYASA_VERI) return;
  const p = portfoyOku();
  let mesajlar = [];
  Object.keys(p).forEach(sym => {
    const k = p[sym];
    if (!k.hedef && !k.stop) return;
    const fiyat = fiyatBul(sym);
    if (fiyat == null) return;
    if (k.hedef && fiyat >= k.hedef && !k.tetik_hedef) {
      k.tetik_hedef = true;
      mesajlar.push(`🎯 ${sym} hedefe ulaştı: ${fmt(fiyat)} TL (hedef ${fmt(k.hedef)})`);
    }
    if (k.stop && fiyat <= k.stop && !k.tetik_stop) {
      k.tetik_stop = true;
      mesajlar.push(`🛑 ${sym} stop'a düştü: ${fmt(fiyat)} TL (stop ${fmt(k.stop)})`);
    }
  });
  if (mesajlar.length) {
    portfoyKaydet(p);
    mesajlar.forEach(m => bildirim('BIST Panel Alarm', m));
  }
}

/* ── window bağları (inline onclick/oninput/onchange için) ── */
Object.assign(window, {
  badge, g05Cipleri, rsiYorum, hacimOranHtml, genislikHtml, mfiYorum, trendHtml,
  squeezeHtml, sparkSVG, reelBistGrafik, reelBistTablo, trRiskHtml, hisseSatir,
  tabloBolum, renderPiyasa, filtrele, csvIndir, portfoyOku, portfoyKaydet,
  fiyatBul, bildirimIzni, bildirim, portfoyHtml, portfoyEkle, portfoySil,
  alarmSifirla, alarmKontrol, PIYASA_VERI
});
