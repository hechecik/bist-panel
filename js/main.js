/* main.js — giriş noktası (G06 parça 2)
   index.html'de yalnızca iskelet ve <script type="module" src="js/main.js">
   kalır. Bu dosya core'u ve bölüm modüllerini içe alır, onları window'a bağlar
   (inline onclick/onchange ve sekme yönetimi için), sekmeleri kurar ve başlatır.

   Taşınanlar (parça 2): piyasa + filtre/portföy/alarm → js/bolum/piyasa.js,
   grafik/mum modalı → js/bolum/grafik.js, karne/senaryo → js/bolum/karne.js.
   Kalan bölümler (haber, fon, takvim, getiri, kripto, ICT, altın) parça 3/4'te
   taşınacak. */
import { utcTarih, fmt, yuzde, ok, tazelik, BAYAT, haftaIciIsGunu, bayatBantMetni,
         bayatBantGuncelle, alEsc, pfOk, pfRenk, sekmeKur } from './core.js';
import { renderPiyasa, alarmKontrol, durum } from './bolum/piyasa.js';
import { renderGrafik } from './bolum/grafik.js';
import { renderSenaryo } from './bolum/karne.js';

async function yukle() {
  try {
    const d = await (await fetch('data/piyasa.json?v=' + Date.now())).json();
    durum.hesapTarihi = (d.sinyaller && d.sinyaller.hesap_tarihi) || '';
    durum.bolunme = (d.saglik && d.saglik.bolunme_duzeltme) || [];
    renderPiyasa(d); renderGrafik(d); renderSenaryo(d); renderHaber(d); renderFon(d);
    getiriYukle(); takvimYukle();
    alarmKontrol(); // 3+6 — fiyat eşik alarmları
    const gun = new Date().getDay();
    const ure = utcTarih(d.uretildi);
    BAYAT.hisse = ure; bayatBantGuncelle();   // G01: bayat veri bandı
    const fark = Math.floor((Date.now() - ure.getTime()) / 60000);
    const lt = document.getElementById('liveText');
    if (gun === 0 || gun === 6) {
      lt.textContent = 'Borsa kapalı · ' + (d.endeks ? d.endeks.tarih + ' kapanış' : '') + ' · ' + ure.toLocaleTimeString('tr-TR', {hour:'2-digit',minute:'2-digit',timeZone:'Europe/Istanbul'});
      document.querySelector('header').classList.add('stale');
    } else if (fark <= 20) {
      lt.textContent = (fark <= 1 ? 'CANLI' : fark + ' dk önce') + ' · ' + ure.toLocaleTimeString('tr-TR', {hour:'2-digit',minute:'2-digit',timeZone:'Europe/Istanbul'});
    } else {
      lt.textContent = '⏳ ' + fark + ' dk önce · ' + ure.toLocaleTimeString('tr-TR', {hour:'2-digit',minute:'2-digit',timeZone:'Europe/Istanbul'});
      document.querySelector('header').classList.add('stale');
    }
  } catch(e) {
    document.getElementById('sec-piyasa').innerHTML = '<div class="empty">Veri yüklenemedi: ' + e.message + '</div>';
  }
}

/* ══════════ HABER (Cryptopanic tarzı: kategori + dil + yön filtreleri, zaman damgası) ══════════ */
const KAT_AD = {'bist':'📊 BIST','altin-maden':'🥇 Altın/Maden','makro':'🏛️ Makro','global':'🌍 Global'};
let haberFiltre = { kategori: '', dil: '', yon: '' };

function zamanGecmis(iso) {
  if (!iso) return '';
  const t = utcTarih(iso).getTime();
  if (isNaN(t)) return '';
  const dk = Math.floor((Date.now() - t) / 60000);
  if (dk < 1) return 'az önce';
  if (dk < 60) return dk + ' dk önce';
  const sa = Math.floor(dk / 60);
  if (sa < 24) return sa + ' saat önce';
  const gn = Math.floor(sa / 24);
  if (gn < 30) return gn + ' gün önce';
  return Math.floor(gn / 30) + ' ay önce';
}

function haberFiltrele(k, v) {
  if (haberFiltre[k] === v) haberFiltre[k] = '';
  else haberFiltre[k] = v;
  renderHaber(PIYASA_VERI);
}

function chip(k, v, etiket, aktifRenk) {
  const aktif = haberFiltre[k] === v;
  return `<button class="chip ${aktif ? 'active' : ''}" style="${aktif ? 'border-color:' + aktifRenk + ';color:' + aktifRenk + ';font-weight:700' : ''}" onclick="haberFiltrele('${k}','${v}')">${etiket}</button>`;
}

function renderHaber(d) {
  const hb = d.haberler || [];
  let html = '<h2>📰 Haber Akışı <span class="cnt">' + hb.length + ' haber · 7 gün</span></h2>';
  html += '<div class="chips">' +
    chip('dil', 'tr', '🇹🇷 Türkçe', 'var(--info)') +
    chip('dil', 'en', '🇬🇧 İngilizce', 'var(--info)') +
    chip('kategori', 'bist', '📊 BIST', 'var(--up)') +
    chip('kategori', 'altin-maden', '🥇 Altın/Maden', 'var(--warn)') +
    chip('kategori', 'makro', '🏛️ Makro', 'var(--info)') +
    chip('kategori', 'global', '🌍 Global', 'var(--accent)') +
    chip('yon', 'pozitif', '🟢 Pozitif', 'var(--up)') +
    chip('yon', 'negatif', '🔴 Negatif', 'var(--down)') +
    (Object.values(haberFiltre).some(Boolean) ? `<button class="chip" onclick="haberFiltre={kategori:'',dil:'',yon:''};renderHaber(PIYASA_VERI)">✕ Temizle</button>` : '') +
    '</div>';

  const filtreli = hb.filter(h =>
    (!haberFiltre.kategori || h.kategori === haberFiltre.kategori) &&
    (!haberFiltre.dil || h.dil === haberFiltre.dil) &&
    (!haberFiltre.yon || h.yon === haberFiltre.yon)
  );

  if (filtreli.length) {
    filtreli.forEach(h => {
      const cls = h.yon === 'pozitif' ? 'b-AL' : (h.yon === 'negatif' ? 'b-SAT' : 'b-TUT');
      const kat = KAT_AD[h.kategori] || h.kategori || '';
      const dil = h.dil === 'tr' ? '🇹🇷' : '🇬🇧';
      const zaman = zamanGecmis(h.yayin_tarihi);
      const ic = `<div class="nm"><span class="badge ${cls}">${h.etiket}</span> ` +
        (h.sembol ? `<b>${h.sembol}</b> ` : '') + h.baslik +
        `<br><small style="color:var(--tx2)">${kat} ${dil} · ${h.kaynak || ''} · <b style="color:var(--tx)">${zaman}</b></small></div>`;
      html += h.link
        ? `<a class="ev" style="text-decoration:none;color:inherit" href="${h.link}" target="_blank" rel="noopener">${ic}</a>`
        : `<div class="ev">${ic}</div>`;
    });
    html += '<div class="note">Kaynaklar: Yahoo Finance (BIST + altın/gümüş) · Habertürk · Fortune TR · Paratic · Bloomberg HT · CNBC Ekonomi/Dünya · Investing.com · Google News (KAP bildirim + TR borsa + global makro). Etiketler anahtar kelime kurallarıyla otomatik — uydurma yorum yok. Başlığa tıkla → kaynağa git.</div>';
  } else {
    html += '<div class="empty">Bu filtreye uyan haber yok</div>';
  }

  // Tarama (mevcut)
  const tr = d.sinyaller && d.sinyaller.tarama;
  if (tr) {
    html += '<h2>🔍 Aşırı Satım (RSI &lt; 30) <span class="cnt">' + (tr.asiri_satim||[]).length + '</span></h2>';
    html += (tr.asiri_satim && tr.asiri_satim.length)
      ? '<div class="chips">' + tr.asiri_satim.map(r => `<span class="chip"><b style="color:var(--info)">${r.sembol}</b> ${fmt(r.fiyat)} <span class="r">RSI ${fmt(r.rsi,0)} · ${r.sinyal}</span></span>`).join('') + '</div>'
      : '<div class="empty" style="padding:6px 0">Yok</div>';
    html += '<h2>🔴 Aşırı Alım (RSI &gt; 75) <span class="cnt">' + (tr.asiri_alim||[]).length + '</span></h2>';
    html += (tr.asiri_alim && tr.asiri_alim.length)
      ? '<div class="chips">' + tr.asiri_alim.map(r => `<span class="chip"><b style="color:var(--down)">${r.sembol}</b> ${fmt(r.fiyat)} <span class="r">RSI ${fmt(r.rsi,0)} · ${r.sinyal}</span></span>`).join('') + '</div>'
      : '<div class="empty" style="padding:6px 0">Yok</div>';
    html += '<h2>🟢 MACD Güçlü (skor ≥ 2) <span class="cnt">' + (tr.macd_guclu||[]).length + '</span></h2>';
    html += (tr.macd_guclu && tr.macd_guclu.length)
      ? '<div class="chips">' + tr.macd_guclu.map(r => `<span class="chip"><b style="color:var(--up)">${r.sembol}</b> ${fmt(r.fiyat)} <span class="r">${r.sinyal} · skor ${r.skor > 0 ? '+' : ''}${r.skor}</span></span>`).join('') + '</div>'
      : '<div class="empty" style="padding:6px 0">Yok</div>';
  }

  // Takvim (mevcut, alta taşındı)
  html += '<h2>📅 Ekonomik Takvim</h2>';
  if (d.takvim && d.takvim.length) {
    d.takvim.slice(0, 10).forEach(ev => {
      const cls = ev.onem === 'high' ? 'hi' : (ev.onem === 'mid' ? 'mi' : '');
      html += `<div class="ev"><div class="dt">${ev.tarih}</div><div class="tm">${ev.saat}</div>` +
              `<div class="nm"><span class="${cls}">${ev.ulke}</span> · ${ev.olay}</div></div>`;
    });
  } else html += '<div class="empty">Takvim verisi yok</div>';

  document.getElementById('sec-haber').innerHTML = html;
}

/* ══════════ FON ══════════ */
const SEKTOR_TR = {'Industrials':'Sanayi','Financial Services':'Finans','Basic Materials':'Hammadde',
  'Consumer Cyclical':'Tüketici','Consumer Defensive':'Temel Tüketim','Technology':'Teknoloji',
  'Communication Services':'İletişim','Energy':'Enerji','Utilities':'Kamu Hizmetleri',
  'Real Estate':'Gayrimenkul','Healthcare':'Sağlık'};
const sekTr = s => SEKTOR_TR[s] || s || '—';

function renderFon(d) {
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

/* ══════════ SABİT GETİRİ (devlet tahvili + eurobond) ══════════ */
async function getiriYukle() {
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

/* ══════════ TAKVİM (Halka Arz + Temettü) ══════════ */
function durumEtiket(d) {
  const m = {
    yaklasan: ['Yaklaşan', 'var(--up)'], tamamlandi: ['Tamamlandı', 'var(--tx2)'],
    ertelendi: ['Ertelendi', 'var(--warn)'], iptal: ['İptal', 'var(--down)'],
    basvuru: ['Başvuruda', 'var(--warn)'], bilinmiyor: ['—', 'var(--tx2)']
  };
  const x = m[d] || m.bilinmiyor;
  return `<span style="color:${x[1]}">${x[0]}</span>`;
}

async function takvimYukle() {
  const el = document.getElementById('sec-takvim');
  if (!el) return;
  try {
    const t = await (await fetch('data/takvim.json?v=' + Date.now())).json();
    let h = '<h2>📅 Halka Arz Takvimi <span class="cnt">' + (t.halka_arz ? t.halka_arz.length : 0) + ' kayıt</span></h2>';

    if (t.basvuru && t.basvuru.length) {
      h += '<div class="note">🟡 <b>Başvuru sürecinde</b> (henüz tarih/kod yok): ' + t.basvuru.slice(0, 24).map(x => x).join(' · ') + '</div>';
    }

    if (t.halka_arz && t.halka_arz.length) {
      h += '<div class="twrap"><table><tr><th>Kod</th><th>Şirket</th><th>Tarih</th><th>Durum</th></tr><tbody>';
      t.halka_arz.forEach(x => {
        h += `<tr><td class="sym">${x.kod || '—'}</td><td>${x.sirket || ''}</td><td>${x.tarih || '—'}</td><td>${durumEtiket(x.durum)}</td></tr>`;
      });
      h += '</tbody></table></div>';
    } else {
      h += '<div class="empty">Halka arz listesi boş.</div>';
    }

    if (t.ertelenen && t.ertelenen.length) {
      h += '<h2>⏸️ Ertelenen / İptal <span class="cnt">' + t.ertelenen.length + '</span></h2>' +
        '<div class="twrap"><table><tr><th>Kod</th><th>Şirket</th><th>Tarih</th></tr><tbody>';
      t.ertelenen.forEach(x => { h += `<tr><td class="sym">${x.kod || '—'}</td><td>${x.sirket || ''}</td><td>${x.tarih || '—'}</td></tr>`; });
      h += '</tbody></table></div>';
    }

    if (t.temettu && t.temettu.length) {
      h += '<h2>💰 Temettü Takvimi <span class="cnt">' + t.temettu.length + ' kayıt</span></h2>' +
        '<div class="twrap"><table><tr><th>Kod</th><th>Şirket</th><th>Tarih</th><th>Net Temettü</th><th>Verim</th><th>Durum</th></tr><tbody>';
      t.temettu.slice(0, 40).forEach(x => {
        h += `<tr><td class="sym">${x.kod || '—'}</td><td>${x.sirket || ''}</td><td>${x.tarih || '—'}</td>` +
          `<td>${x.net == null ? '—' : fmt(x.net, 4)}</td><td>${x.yuzde == null ? '—' : '%' + fmt(x.yuzde, 2)}</td>` +
          `<td>${x.gecmis ? '<span style="color:var(--tx2)">geçti</span>' : (x.gun_fark != null && x.gun_fark >= 0 ? `<span class="up">${x.gun_fark} gün sonra</span>` : '—')}</td></tr>`;
      });
      h += '</tbody></table></div>';
    }

    h += `<div class="note">Kaynak: halkarz.com · üretildi ${t.uretildi || ''}. Halka arz tarihleri kesinleşmemiş olabilir — başvuru öncesi resmi KAP bildirimini doğrula.</div>`;
    el.innerHTML = h;
  } catch (e) {
    el.innerHTML = '<h2>📅 Takvim</h2><div class="empty">Takvim verisi yüklenemedi: ' + (e && e.message ? e.message : e) + '</div>';
  }
}

/* ══════════ KRİPTO ══════════ */
let KRIPTO_VERI = null;

// fiyat kısaltma: coin başına anlamlı hassasiyet (BTC 82.508,00 / SHIB 0,0000123)
function krFiyat(n) {
  if (n == null) return '—';
  const a = Math.abs(n);
  const h = a >= 1000 ? 2 : a >= 1 ? 2 : a >= 0.01 ? 4 : 8;
  return Number(n).toLocaleString('tr-TR', {minimumFractionDigits: h, maximumFractionDigits: h});
}
// büyük sayı kısaltma: 2,91 T / 139,4 Mr
function krBuyuk(n) {
  if (n == null) return '—';
  const a = Math.abs(n);
  if (a >= 1e12) return fmt(n / 1e12, 2) + ' T';
  if (a >= 1e9) return fmt(n / 1e9, 1) + ' Mr';
  if (a >= 1e6) return fmt(n / 1e6, 1) + ' M';
  return fmt(n, 0);
}

function renderKripto(d) {
  KRIPTO_VERI = d;
  const coinler = d.coinler || [];
  let html = '<h2>🪙 Kripto Piyasa <span class="cnt">' + coinler.length + ' coin</span>';
  if (d.kaynak) html += `<span class="fresh${d.kaynak === 'coingecko' ? ' ok' : ''}">${d.kaynak}</span>`;
  html += '</h2>';

  // ── Global + Korku endeksi kartları ──
  const gl = d.global || {}, k = d.korku;
  if (gl.toplam_piyasa_degeri != null || gl.btc_dominans != null || k) {
    html += '<div class="scn">';
    if (gl.toplam_piyasa_degeri != null)
      html += `<div class="sc"><div class="t">Toplam Piyasa Değeri</div><div class="o">$${krBuyuk(gl.toplam_piyasa_degeri)}</div>` +
        `<div class="m">24s <b class="${ok(gl.degisim_24s)}">${yuzde(gl.degisim_24s)}</b>` +
        (gl.toplam_hacim != null ? ` · hacim $${krBuyuk(gl.toplam_hacim)}` : '') + '</div></div>';
    if (gl.btc_dominans != null)
      html += `<div class="sc"><div class="t">BTC Dominans</div><div class="o">%${gl.btc_dominans}</div>` +
        `<div class="m">${gl.eth_dominans != null ? 'ETH %' + gl.eth_dominans : ''}` +
        (gl.aktif_coin ? (gl.eth_dominans != null ? ' · ' : '') + gl.aktif_coin.toLocaleString('tr-TR') + ' aktif coin' : '') + '</div></div>';
    if (k) {
      const renk = k.deger < 25 ? 'var(--down)' : k.deger > 75 ? 'var(--up)' : 'var(--warn)';
      html += `<div class="sc wide"><div class="t">😱 Korku &amp; Açgözlülük Endeksi</div>` +
        `<div class="o" style="color:${renk}">${k.deger} <span style="font-size:13px">${k.etiket}</span></div>` +
        `<div class="bar"><i style="width:${k.deger}%;background:${renk}"></i></div>` +
        (k.onceki != null ? `<div class="m">Önceki: <b>${k.onceki}</b></div>` : '') + '</div>';
    }
    html += '</div>';
  }

  // ── Coin kartları ──
  if (!coinler.length) {
    html += '<div class="empty">Kripto verisi şu an yok — bir sonraki güncellemede</div>';
  } else {
    html += '<h2>📊 Coinler <span class="cnt">skor · sinyal</span></h2><div class="kr-grid">';
    coinler.forEach(c => {
      const d24 = c.degisim_24s, d7 = c.degisim_7g, st = c.sinyal === 'PARİTE';
      const skRenk = c.skor >= 2 ? 'var(--up)' : c.skor <= -2 ? 'var(--down)' : 'var(--tx2)';
      html += `<div class="kr" data-sym="${c.sembol}">` +
        `<div class="hd"><span class="ksym">${c.sembol}</span>` +
          (c.sira ? `<span class="rank">#${c.sira}</span>` : '') +
          `<span class="nm">${c.ad || ''}</span></div>` +
        `<div class="pz">$${krFiyat(c.fiyat)}</div>` +
        (c.fiyat_tl != null ? `<div class="tl">₺${krFiyat(c.fiyat_tl)}</div>` : '') +
        `<div class="ch">` +
          `<span class="${ok(d24)}">${yuzde(d24)} <span class="lb">24s</span></span>` +
          (d7 != null ? `<span class="${ok(d7)}">${yuzde(d7)} <span class="lb">7g</span></span>` : '') +
        `</div>` +
        `<div class="sp">${sparkSVG(c)}</div>` +
        `<div class="ft">` +
          (st ? '<span class="stable">PARİTE · stablecoin</span>'
              : `<span class="kskor" style="color:${skRenk}">${c.skor > 0 ? '+' : ''}${c.skor}</span>${badge(c.sinyal)}`) +
        `</div>` +
        (!st && c.skor !== 0 && c.nedenler && c.nedenler.length
          ? `<div class="note2">▸ ${c.nedenler[0]}</div>` : '') +
        `</div>`;
    });
    html += '</div>';
  }

  if (d.not) html += `<div class="note">${d.not}` +
    (d.ureildi ? ` · Son veri: ${new Date(d.ureildi).toLocaleString('tr-TR', {day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit'})}` : '') +
    '</div>';
  document.getElementById('sec-kripto').innerHTML = html;
}

async function kriptoYukle() {
  const sec = document.getElementById('sec-kripto');
  if (!KRIPTO_VERI) sec.innerHTML = '<div class="empty">Kripto verisi yükleniyor…</div>';
  try {
    const d = await (await fetch('data/kripto.json?v=' + Date.now())).json();
    renderKripto(d);
  } catch (e) {
    if (!KRIPTO_VERI) sec.innerHTML = '<div class="empty">Kripto verisi yüklenemedi: ' + e.message + '</div>';
  }
}

/* ── ICT TARAYICI (Katman 2 — PineScript→Python mantığı) ── */
function ictListe(baslik, ikon, items, satirFn) {
  if (!items || !items.length) return '';
  let h = `<h2>${ikon} ${baslik} <span class="cnt">${items.length}</span></h2><div class="ict-list">`;
  items.forEach(x => { h += `<div class="ict-row">${satirFn(x)}</div>`; });
  return h + '</div>';
}
const ictYon = y => `<span class="tag ${y === 'BULLISH' ? 'up' : 'dn'}">${y === 'BULLISH' ? '▲ ALIŞ' : '▼ SATIŞ'}</span>`;

function renderIct(d) {
  const sec = document.getElementById('sec-ict');
  const t = d && d.ict_tarama;
  if (!t) { sec.innerHTML = '<div class="empty">ICT verisi bekleniyor — bir sonraki veri güncellemesinde gelecek</div>'; return; }
  const al = t.al || [], sat = t.sat || [];
  let html = '<h2>🧭 ICT Tarayıcı <span class="cnt">' + (t.islenen || 0) + ' hisse tarandı</span>' +
             '<span class="fresh ok">PineScript→Python</span></h2>';

  const kart = (etiket, deger, renk) => `<div class="sc"><div class="t">${etiket}</div><div class="o" style="color:${renk}">${deger}</div></div>`;
  html += '<div class="scn">' +
    kart('AL · skor ≥3', al.length, 'var(--up)') +
    kart('SAT · skor ≤-3', sat.length, 'var(--down)') +
    kart('MSS ↑ / ↓', (t.mss_yukari || []).length + ' / ' + (t.mss_asagi || []).length, 'var(--info)') +
    kart('OB içinde', (t.ob_ici || []).length, 'var(--warn)') +
    kart('FVG açık', (t.fvg_acik || []).length, 'var(--accent)') +
    kart('EQH / EQL', (t.eqh || []).length + ' / ' + (t.eql || []).length, 'var(--tx2)') +
    '</div>';

  html += ictListe('AL Sinyali (ICT skor ≥3)', '🟢', al, x =>
    `<span class="sym">${x.sembol}</span><span class="px">${fmt(x.fiyat)}</span>` +
    `<span class="skor" style="color:var(--up)">+${x.skor}</span>` +
    `<span class="dsc">${(x.nedenler || [])[0] || ''}</span>`);
  html += ictListe('SAT Sinyali (ICT skor ≤-3)', '🔴', sat, x =>
    `<span class="sym">${x.sembol}</span><span class="px">${fmt(x.fiyat)}</span>` +
    `<span class="skor" style="color:var(--down)">${x.skor}</span>` +
    `<span class="dsc">${(x.nedenler || [])[0] || ''}</span>`);
  html += ictListe('Yapı Kırılımı ↑ (MSS / BOS)', '⬆️', t.mss_yukari, x =>
    `<span class="sym">${x.sembol}</span><span class="px">${fmt(x.fiyat)}</span>${ictYon('BULLISH')}<span class="dsc">${x.aciklama}</span>`);
  html += ictListe('Yapı Kırılımı ↓ (MSS / BOS)', '⬇️', t.mss_asagi, x =>
    `<span class="sym">${x.sembol}</span><span class="px">${fmt(x.fiyat)}</span>${ictYon('BEARISH')}<span class="dsc">${x.aciklama}</span>`);
  html += ictListe('Order Block İçinde (giriş bölgesi)', '📦', t.ob_ici, x =>
    `<span class="sym">${x.sembol}</span><span class="px">${fmt(x.fiyat)}</span>${ictYon(x.yon)}<span class="dsc">OB bölgesi ${fmt(x.alt)} – ${fmt(x.ust)}</span>`);
  html += ictListe('FVG Açık (dolmamış boşluk)', '🕳️', t.fvg_acik, x =>
    `<span class="sym">${x.sembol}</span><span class="px">${fmt(x.fiyat)}</span>${ictYon(x.yon)}<span class="dsc">FVG ${fmt(x.alt)} – ${fmt(x.ust)} · fiyat: ${x.konum}</span>`);
  html += ictListe('Likidite Süpürmesi (stop avı)', '💧', t.sweep, x =>
    `<span class="sym">${x.sembol}</span>${ictYon(x.yon)}<span class="dsc">${x.aciklama}</span>`);
  html += ictListe('Eşit Yüksekler (üstte likidite havuzu)', '🟰', t.eqh, x =>
    `<span class="sym">${x.sembol}</span><span class="dsc">EQH ≈ ${fmt(x.seviye)} — süpürme hedefi</span>`);
  html += ictListe('Eşit Düşükler (altta likidite havuzu)', '🟰', t.eql, x =>
    `<span class="sym">${x.sembol}</span><span class="dsc">EQL ≈ ${fmt(x.seviye)} — süpürme hedefi</span>`);

  if (!al.length && !sat.length) html += '<div class="empty">Bugün ICT skoru eşiği (±3) aşan hisse yok — yapı/OB/FVG listeleri yine de geçerli.</div>';
  if (t.kural) {
    html += `<div class="ict-not">📐 <b>Skor kuralı</b> — ${t.kural}<br>` +
      (t.hesap_tarihi ? `Tarama zamanı: ${t.hesap_tarihi} · ` : '') +
      `Mantık kaynağı: ArunKBhaskar/PineScript (MPL-2.0) → <code>scripts/ict.py</code> (TradingView'siz, Python).</div>`;
  }

  // ── SÖZLÜK (kısa bilgilendirme — hem panelde hem sözlü olarak) ──
  html += '<h2>📚 ICT Sözlüğü <span class="cnt">bu listeler ne anlatıyor</span></h2><div class="ict-soz">';
  html += [
    ['MSS · Piyasa Yapı Kayması', 'Market Structure Shift — fiyatın son tepe/dip yapısını kırıp yön değiştirmesi. ↑ = düşüş yapısı bozuldu (alış), ↓ = yükseliş yapısı bozuldu (satış).'],
    ['BOS · Yapı Kırılımı', 'Break of Structure — trend yönünde bir önceki tepe/dip kırılır; trendin devamı sayılır.'],
    ['FVG · Adil Değer Boşluğu', 'Fair Value Gap — 3 mumluk hızlı hareketin bıraktığı fiyat boşluğu; fiyat çoğu zaman geri dönüp bu boşluğu doldurur.'],
    ['OB · Order Block', 'Kurumsal emir bölgesi — büyük hareketin başladığı son ters mum; fiyat dönünce bu bölgeden tepki verir (giriş bölgesi).'],
    ['EQH / EQL', 'Eşit Yüksekler / Eşit Düşükler — aynı seviyedeki iki tepe/dip; üstü/altı biriken stop emirleri = likidite havuzu.'],
    ['Süpürme · stop avı', 'Likidite süpürmesi — fiyat EQH/EQL seviyesini hızla delip geri döner; stopları tetikleyip asıl yönün başlangıcı.'],
    ['Likidite', 'Fiyatın çekildiği emir yığınları — stop-loss ve bekleyen emirlerin toplandığı seviyeler.'],
    ['Displacement', 'Yer değiştirme — FVG/OB bırakan güçlü, tek yönlü impuls mum (kurumsal giriş işareti).']
  ].map(([b, tt]) => `<div class="k"><b>${b}</b>${tt}</div>`).join('');
  html += '</div>';

  // ── SENARYO OKUMASI (geçmiş → şimdi → gelecek) ──
  const yon = al.length > sat.length ? 'YUKARI (alış ağır)' : sat.length > al.length ? 'AŞAĞI (satış ağır)' : 'NÖTR (dengeli)';
  let gelecek;
  if (al.length > sat.length) gelecek = 'Alış sinyali veren hisselerde FVG/OB bölgesine geri çekilme alım fırsatı; üstteki EQH likiditesi hedef. SAT tarafında yapı bozulursa aşağı süpürme riski var.';
  else if (sat.length > al.length) gelecek = 'Satış sinyali ağır — aşağı yapı kırılımları sürerse destek süpürmeleri (EQL) beklenir; alış için FVG/OB tepkisi teyit edilmeli.';
  else gelecek = 'Sinyaller dengeli — teyit için MSS yönü ve FVG dolumu izlenmeli; net yön gelene kadar bekle-gör.';
  html += '<div class="ict-not" style="border-style:solid">🔭 <b>Senaryo okuması</b><br>' +
    `<b>Şimdi:</b> ${t.islenen || 0} hisse tarandı · ${al.length} alış / ${sat.length} satış → genel eğilim ${yon}. ` +
    `${(t.mss_yukari || []).length} yukarı / ${(t.mss_asagi || []).length} aşağı yapı kırılımı, ${(t.fvg_acik || []).length} açık FVG, ` +
    `${(t.eqh || []).length} EQH / ${(t.eql || []).length} EQL, ${(t.sweep || []).length} likidite süpürmesi.<br>` +
    `<b>Gelecek:</b> ${gelecek}</div>`;

  sec.innerHTML = html;
}

async function ictYukle() {
  const sec = document.getElementById('sec-ict');
  if (!PIYASA_VERI) {
    sec.innerHTML = '<div class="empty">Veri yükleniyor…</div>';
    try { PIYASA_VERI = await (await fetch('data/piyasa.json?v=' + Date.now())).json(); }
    catch (e) { sec.innerHTML = '<div class="empty">Veri yüklenemedi: ' + e.message + '</div>'; return; }
  }
  renderIct(PIYASA_VERI);
}

/* ── ALTIN (ONS) BÖLÜMÜ ── */
let ALTIN_VERI = null;
function renderAltin(d) {
  const sec = document.getElementById('sec-altin');
  if (!d || !d.fiyat) { sec.innerHTML = '<div class="empty">Altın verisi bekleniyor — bir sonraki güncellemede gelecek</div>'; return; }
  const f = d.fiyat, v = d.vital || {}, s = d.senaryo || {}, sv = d.seviyeler || {};
  const biasK = s.bias === 'BOĞA' ? 'boga' : s.bias === 'AYI' ? 'ayi' : 'notr';
  const d1 = (f.performans && f.performans['1g']) || 0;
  let h = '';

  h += '<h2>🥇 Ons Altın <span class="fresh ok">ons bazlı</span></h2>';
  // Tazelik: hafta içi üretildi 90 dakikadan eskiyse bayat
  {
    const gun = utcTarih(d.uretildi);
    const haftaIci = gun.getDay() >= 1 && gun.getDay() <= 5;
    const bayat = haftaIci && (Date.now() - gun.getTime()) > 90 * 60 * 1000;
    h += `<div class="fresh ${bayat ? 'bayat' : 'ok'}" style="margin-bottom:6px">${bayat ? 'veri bayat — son güncelleme 90+ dk önce' : 'veri güncel'}</div>`;
  }
  const vadeli = f.kaynak_tipi === 'vadeli';
  h += `<div class="ex-card">
     <div class="ex-label">XAU/USD${vadeli ? ' <span class="badge">VADELİ</span>' : (f.spot ? ' · canlı spot ' + fmt(f.spot) + '$' : '')}</div>
     <div class="ex-val">${fmt(f.ons)}<span style="font-size:15px;color:var(--tx2)"> $/ons</span></div>
     <div class="ex-chg ${d1>=0?'up':'down'}">${pfOk(d1)} <span style="color:var(--tx2);font-size:11px">bugün</span></div>
     <div class="ex-sub">
       <span>Gram/TL: <b style="color:var(--tx)">${f.gram_tl ? fmt(f.gram_tl) : '—'}</b></span>
       <span>USDTRY: ${f.usdtry || '—'}</span>
       <span>Veri tarihi: ${f.son_tarih || '—'}</span>
     </div></div>`;

  h += '<div class="al-perf">';
  [['1h','1 hafta'],['2h','2 hafta'],['1a','1 ay'],['3a','3 ay'],['6a','6 ay'],['1y','1 yıl']].forEach(([k, lb]) => {
    const val = f.performans ? f.performans[k] : undefined;
    if (val === undefined || val === null) return;
    h += `<div class="p">${lb} <b style="color:${pfRenk(val)}">${pfOk(val)}</b></div>`;
  });
  h += '</div>';

  // VİTALLER
  h += '<h2>🩺 Vitaller</h2><div class="scn">';
  h += `<div class="sc"><div class="t">TREND · MA20/50/200</div><div class="o" style="color:${(v.trend_skor||0)>=1?'var(--up)':(v.trend_skor||0)<=-1?'var(--down)':'var(--warn)'}">${v.trend || '—'}</div><div class="m">MA20 <b>${fmt(v.ma20)}</b> · MA50 <b>${fmt(v.ma50)}</b> · MA200 <b>${fmt(v.ma200)}</b></div></div>`;
  h += `<div class="sc"><div class="t">RSI (14)</div><div class="o" style="color:${v.rsi>=55?'var(--up)':v.rsi<45?'var(--down)':'var(--warn)'}">${v.rsi == null ? '—' : v.rsi}</div><div class="m">${v.rsi_yorum || ''}</div></div>`;
  h += `<div class="sc"><div class="t">52-HAFTA KONUMU</div><div class="o">${v.konum_52h == null ? '—' : v.konum_52h + '%'}</div><div class="m">${v.konum_yorum || ''} · ${fmt(v.l52)}–${fmt(v.h52)}$</div></div>`;
  h += `<div class="sc"><div class="t">OYNAKLIK · ATR (14)</div><div class="o">${fmt(v.atr)}$</div><div class="m">günlük hareket ≈ %${v.atr_yuzde == null ? '—' : v.atr_yuzde}</div></div>`;
  h += '</div>';

  // SEVİYELER
  const lvBox = (baslik, dizi, renk) => {
    let b = `<div class="box"><h3>${baslik}</h3>`;
    if (!dizi || !dizi.length) b += '<div class="lv"><span class="tp">veri yok</span></div>';
    (dizi || []).forEach(x => {
      b += `<div class="lv"><span class="tp">${alEsc(x.tip)}</span><b style="color:${renk}">${fmt(x.seviye)}$</b>` +
           `<span class="dz" style="color:${renk}">${x.mesafe_pct >= 0 ? '+' : ''}${x.mesafe_pct}%</span></div>`;
    });
    return b + '</div>';
  };
  h += '<h2>📊 Destek / Direnç (ons)</h2><div class="al-lv">' +
       lvBox('🔴 DİRENÇ · üstü', sv.direnc, 'var(--down)') +
       lvBox('🟢 DESTEK · altı', sv.destek, 'var(--up)') + '</div>';

  // SENARYO
  h += `<h2>🔭 Senaryo <span class="al-bi ${biasK}">${s.bias || '—'} · skor ${s.bias_skor == null ? '' : (s.bias_skor > 0 ? '+' : '') + s.bias_skor}</span></h2>`;
  h += '<div class="scn">' +
       `<div class="sc wide"><div class="t">GEÇMİŞ · nereden geldi</div><div class="m" style="font-size:11.5px">${alEsc(s.gectmis)}</div></div>` +
       `<div class="sc wide"><div class="t">ŞU AN · durum</div><div class="m" style="font-size:11.5px">${alEsc(s.durum)}</div></div>` +
       `<div class="sc"><div class="t">YUKARI SENARYO · tetik ${fmt(s.yukari && s.yukari.tetik)}$</div><div class="m">${alEsc(s.yukari && s.yukari.metin)}${s.yukari && s.yukari.gecersiz != null ? `<br><span style="color:var(--tx2);font-size:10.5px">geçersizlik: ${fmt(s.yukari.gecersiz)}$ altı</span>` : ''}</div></div>` +
       `<div class="sc"><div class="t">AŞAĞI SENARYO · tetik ${fmt(s.asagi && s.asagi.tetik)}$</div><div class="m">${alEsc(s.asagi && s.asagi.metin)}${s.asagi && s.asagi.gecersiz != null ? `<br><span style="color:var(--tx2);font-size:10.5px">geçersizlik: ${fmt(s.asagi.gecersiz)}$ üstü</span>` : ''}</div></div>` +
       '</div>';

  // MAKRO SÜRÜCÜLER + FOMC SAYACI (G10) — kendi try/catch'i, düşerse diğer bloklar sürer
  try {
    const mk = d.makro || {};
    const fomc = mk.fomc || {};
    if (fomc.metin) {
      const sepB = fomc.sep ? '<span class="badge hi">SEP VAR</span>' : '<span class="badge mi">SEP YOK</span>';
      h += `<h2>🏛️ FOMC Sayacı</h2><div class="scn"><div class="sc wide">` +
           `<div class="t">${sepB} SONRAKİ KARAR</div>` +
           `<div class="o" style="font-size:15px">${alEsc(fomc.tarih)} · ${alEsc(fomc.saat_tsi)} TSİ</div>` +
           `<div class="m"><b>${fomc.kalan_gun} gün</b> kaldı · ${alEsc(fomc.metin)}</div></div></div>`;
      if ((fomc.sonraki_liste || []).length > 1) {
        h += '<div class="scn" style="margin-top:6px">';
        fomc.sonraki_liste.slice(0, 5).forEach(x => {
          h += `<div class="sc"><div class="t">${alEsc(x.tarih)} ${x.sep ? '· SEP' : ''}</div>` +
               `<div class="o" style="font-size:13px">${alEsc(x.tsi)} TSİ</div></div>`;
        });
        h += '</div>';
      }
    }

    if (mk.durum === 'veri yok') {
      h += '<h2>🌐 Makro Sürücüler</h2><div class="scn"><div class="sc wide"><div class="t">MAKRO</div>' +
           '<div class="o">veri yok</div><div class="m">FRED/yfinance kaynaklarına ulaşılamadı — altın blokları etkilenmedi.</div></div></div>';
    } else {
      const sr = mk.seriler || {}, py = mk.piyasa || {};
      const korR = k => k == null ? '—' : `<b style="color:${k >= 0.5 ? 'var(--up)' : k <= -0.5 ? 'var(--down)' : 'var(--tx2)'}">${k.toFixed(2)}</b>`;
      const chg = (v, bp) => {
        if (v == null) return '—';
        const s = (v > 0 ? '+' : '') + (bp ? Math.round(v * 100) + ' bp' : v.toFixed(2));
        return `<span style="color:${v > 0 ? 'var(--up)' : v < 0 ? 'var(--down)' : 'var(--tx2)'}">${s}</span>`;
      };
      const satir = (ad, o, bp) => {
        if (!o || o.durum === 'veri yok') return `<div class="lv"><span class="tp">${alEsc(ad)}</span><b>veri yok</b></div>`;
        return `<div class="lv"><span class="tp">${alEsc(ad)}</span>` +
               `<b>${fmt(o.son, bp ? 2 : 2)}${bp ? '%' : ''}</b>` +
               `<span class="dz">5g ${chg(o.degisim_5g, bp)} · 20g ${chg(o.degisim_20g, bp)}</span>` +
               `<span class="dz" title="ons ile 60 günlük korelasyon">r=${korR(o.korelasyon_60g)}</span></div>`;
      };
      h += '<h2>🌐 Makro Sürücüler <span class="cnt">ons ile 60g korelasyon</span></h2><div class="al-lv">';
      h += '<div class="box"><h3>💰 Dolar & Petrol</h3>' +
           satir('DXY (dolar endeksi)', py.dxy) + satir('Brent ($/varil)', py.brent) + '</div>';
      h += '<div class="box"><h3>📉 ABD Faiz & Enflasyon</h3>' +
           satir('Reel 10Y (TIPS)', sr.DFII10, true) + satir('10Y nominal', sr.DGS10, true) +
           satir('2Y', sr.DGS2, true) + satir('10Y başabaş', sr.T10YIE, true) + '</div>';
      h += '</div>';
      if (py.brent && py.brent.not) h += `<div class="ict-not">🛢️ ${alEsc(py.brent.not)} Reel 10Y altının 1 numaralı makro sürücüsüdür; r değeri son 60 işlem gününün korelasyonudur.</div>`;
      if (mk.fed_bandi && mk.fed_bandi.ust != null) {
        h += `<div class="ict-not">🏦 Fed politika faizi bandı: <b>%${fmt(mk.fed_bandi.alt)} – %${fmt(mk.fed_bandi.ust)}</b> (FRED DFEDTARL/U, ${alEsc(mk.fed_bandi.tarih)}).</div>`;
      }
    }

    const dp = mk.dot_plot || {};
    if (!dp.durum) {
      const medSir = Object.entries(dp.medyan || {}).filter(([y]) => +y >= new Date().getFullYear());
      const ima = dp.piyasa_ima || {};
      const imaYil = ima.yillar || {};
      const makasRenk = dp.makas_bp == null ? 'var(--tx2)' : dp.makas_bp > 25 ? 'var(--down)' : dp.makas_bp < -25 ? 'var(--up)' : 'var(--warn)';
      h += '<h2>🎯 Dot Plot · Piyasa vs Fed</h2><div class="scn">';
      h += `<div class="sc"><div class="t">DOT PLOT MEDYANI (SEP)</div><div class="o" style="font-size:13px">` +
           (medSir.length ? medSir.map(([y, v]) => `${y}: <b>%${fmt(v, 2)}</b>`).join(' · ') : 'veri yok') +
           `</div><div class="m">Kaynak: FRED FEDTARMD (FOMC SEP medyan fed funds)</div></div>`;
      h += `<div class="sc"><div class="t">PİYASA İMA PATİKASI ${ima.kaynak === 'proxy' ? '<span class="badge mi">PROXY</span>' : '<span class="badge hi">VADELİ</span>'}</div>` +
           `<div class="o" style="font-size:13px">` +
           (Object.keys(imaYil).length ? Object.entries(imaYil).filter(([y]) => +y <= new Date().getFullYear() + 1).map(([y, v]) => `${y}: <b>%${fmt(v, 2)}</b>`).join(' · ') : 'veri yok') +
           `</div><div class="m">${ima.kaynak === 'proxy' ? alEsc(ima.not || 'proxy') : 'ZQ fed funds vadelileri · ima faiz = 100 − fiyat'}</div></div>`;
      h += `<div class="sc"><div class="t">MAKAS · piyasa − dot${dp.makas_yil ? ' (' + dp.makas_yil + ')' : ''}</div>` +
           `<div class="o" style="color:${makasRenk}">${dp.makas_bp == null ? '—' : (dp.makas_bp > 0 ? '+' : '') + dp.makas_bp + ' bp'}</div>` +
           `<div class="m">${alEsc(dp.yorum || 'veri yok')}</div></div>`;
      h += `<div class="sc"><div class="t">SEP REVİZYONU${dp.revizyon_yil ? ' (' + dp.revizyon_yil + ')' : ''}</div>` +
           (dp.revizyon && dp.revizyon.degisim_bp != null
             ? `<div class="o" style="color:${dp.revizyon.degisim_bp > 0 ? 'var(--down)' : dp.revizyon.degisim_bp < 0 ? 'var(--up)' : 'var(--tx2)'}">${dp.revizyon.degisim_bp > 0 ? '+' : ''}${dp.revizyon.degisim_bp} bp</div>` +
               `<div class="m">${alEsc(dp.revizyon.yorum)} · önceki SEP ${alEsc(dp.onceki_sep_tarihi || '—')} → ${alEsc(dp.sep_tarihi || '—')}</div>`
             : `<div class="o">veri yok</div><div class="m">Arşivde önceki SEP yok — ilk SEP kaydı bu çalıştırmada yazıldı${dp.sep_tarihi ? ' (' + alEsc(dp.sep_tarihi) + ')' : ''}.</div>`) +
           `</div>`;
      h += '</div>';
      h += '<div class="ict-not">🎯 +25 bp üstü = piyasa Fed’den şahin, −25 bp altı = güvercin, arada = uyumlu. Hiçbir faiz/olasılık/hedef değeri elle girilmez; SEP revizyonu data/sep_arsiv.json içindeki önceki SEP medyanıyla karşılaştırılarak hesaplanır.</div>';
    }
  } catch (e) {
    h += '<h2>🌐 Makro Sürücüler</h2><div class="scn"><div class="sc wide"><div class="t">MAKRO</div><div class="o">veri yok</div><div class="m">Makro bloğu yüklenemedi — altın sayfasının diğer blokları normal çalışıyor.</div></div></div>';
  }

  // KRİTİK GÜNLER
  if ((d.kritik_gunler || []).length) {
    h += `<h2>🗓️ Kritik Günler <span class="cnt">${d.kritik_gunler.length} olay</span></h2>`;
    d.kritik_gunler.slice(0, 14).forEach(k => {
      const onem = k.onem === 'high' ? '<span class="badge hi">YÜKSEK</span>' : '<span class="badge mi">orta</span>';
      h += `<div class="ev"><div class="dt">${alEsc(k.tarih)}<div style="font-size:9px">${alEsc(k.gun)}</div></div>` +
           `<div class="tm">${alEsc(k.saat)}</div>` +
           `<div class="nm"><b>${alEsc(k.ulke)}</b> ${onem} ${alEsc(k.olay)}` +
           `<div style="font-size:10px;color:var(--tx2);margin-top:2px">↳ ${alEsc(k.neden)}</div></div></div>`;
    });
    h += '<div class="ict-not">🗓️ Altını hareket ettiren yüksek etkili ABD/küresel veriler (enflasyon, faiz, istihdam, perakende). Kaynak: doviz.com ekonomik takvim. Saatler Türkiye (UTC+3).</div>';
  }

  // HABERLER
  if ((d.haberler || []).length) {
    h += `<h2>📰 Altın Haberleri <span class="cnt">${d.haberler.length}</span></h2>`;
    d.haberler.slice(0, 10).forEach(n => {
      h += `<div class="ev"><div class="nm"><a href="${alEsc(n.link)}" target="_blank" rel="noopener" style="color:var(--tx);text-decoration:none">${alEsc(n.baslik)}</a>` +
           `<div style="font-size:9.5px;color:var(--tx2);margin-top:2px">${alEsc(n.kaynak)}${n.yayin_tarihi ? ' · ' + alEsc(utcTarih(n.yayin_tarihi).toLocaleString('tr-TR',{timeZone:'Europe/Istanbul',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})) : ''}</div></div></div>`;
    });
  }

  // ── G11: SKOR AYRIMI (teknik / makro) + ayrışma uyarısı ──
  if (d.skorlar) {
    const sk = d.skorlar;
    const isr = (x, y) => x == null ? '<span style="color:var(--tx2)">veri yok</span>'
      : `<b style="color:${x > 0 ? 'var(--up)' : x < 0 ? 'var(--down)' : 'var(--tx2)'}">${x > 0 ? '+' : ''}${x}</b>`;
    h += `<h2>🧭 Skor Ayrımı <span class="cnt">teknik ${sk.teknik ?? '—'} · makro ${sk.makro ?? '—'}${sk.makro_maks ? '/' + sk.makro_maks : ''}</span></h2>`;
    if (sk.ayrisim) h += `<div class="ict-not" style="border-left:3px solid var(--down);color:var(--tx)">${alEsc(sk.ayrisim_metin)}</div>`;
    else h += `<div class="ict-not">${alEsc(sk.ayrisim_metin)}</div>`;
    h += `<div class="sc"><div class="t">TEKNİK SKOR</div><div class="v">${isr(sk.teknik)}</div>` +
         `<div class="m">${alEsc(sk.teknik_yorum)} · trend ±2, RSI ±1, 1 aylık performans ±1 (mekanik, tekrar sayım yok)</div></div>`;
    const mb = sk.makro_bilesenler || {};
    const adlar = { reel_faiz: 'Reel faiz (DFII10)', dxy: 'DXY', dot_makas: 'Dot plot makası', brent: 'Brent' };
    const satirlar = Object.keys(adlar).filter(k => mb[k]).map(k => {
      const b = mb[k];
      return `<div class="lv"><span class="tp">${alEsc(adlar[k])}</span><span>${b.deger > 0 ? '+' : ''}${b.deger}${alEsc(b.birim)}</span>` +
             `<b style="color:${b.puan > 0 ? 'var(--up)' : b.puan < 0 ? 'var(--down)' : 'var(--tx2)'}">${b.puan > 0 ? '+' : ''}${b.puan}</b></div>`;
    }).join('');
    h += `<div class="sc"><div class="t">MAKRO SKOR</div><div class="v">${isr(sk.makro)}</div><div class="m">${alEsc(sk.makro_yorum)} · her bileşen ±1</div>${satirlar}` +
         (sk.esikler_dogrulanmamis ? `<div class="m" style="margin-top:4px">⚠️ Eşikler doğrulanmamış başlangıç değerleri — log/IC denetimi bekliyor.</div>` : '') + `</div>`;
  }

  // ── G11: 4 SENARYO (EĞER → gözlenebilir tetik → ons bandı) ──
  if (d.senaryolar && (d.senaryolar.liste || []).length) {
    const sn = d.senaryolar;
    h += `<h2>🎯 Senaryolar <span class="cnt">ATR×√5 · ATR ${sn.atr != null ? sn.atr : '—'}$</span></h2>`;
    sn.liste.forEach(s => {
      const b = s.bant || [];
      // bant_gosterim: yön tek ise (yukarı/aşağı) bant yerine o yönün seviyesi gösterilir
      const bg = s.bant_gosterim || b;
      const gerc = s.gerceklesti ? ' <span class="badge hi">TETİKLENDİ</span>' : '';
      h += `<div class="sc" style="${s.cakisma ? 'border-left:3px solid var(--down)' : ''}">` +
           `<div class="t">${alEsc(s.ad)}${gerc}${s.olasilik != null ? ' · olasılık %' + s.olasilik : ''}</div>` +
           `<div class="v">${bg[0] != null ? (s.vurgu && bg[0] === bg[1] ? '≈ ' + bg[0] + '$ (tek yön)' : bg[0] + ' – ' + bg[1] + '$') : 'bant yok'}</div>` +
           `<div class="m">EĞER ${alEsc(s.kosul)}<br>Tetik: ${alEsc(s.tetik)} · k=${s.k}` +
           (s.vurgu ? ` · <b style="color:${s.vurgu === 'üst' ? 'var(--up)' : 'var(--down)'}">${alEsc(s.yon)} yön: ${s.vurgu} bant ${s.vurgu === 'üst' ? b[1] : b[0]}$</b>` : '') + `</div></div>`;
    });
    if (sn.not) h += `<div class="ict-not">${alEsc(sn.not)}</div>`;
  }

  // ── G11: GRAM AYRIŞIMI (Δgram ≈ Δons + ΔUSDTRY) ──
  if (d.gram_ayrisim && d.gram_ayrisim.donemler) {
    const ga = d.gram_ayrisim, dn = ga.donemler || {};
    const etiket = { '1g': '1 gün', '1h': '1 hafta', '1a': '1 ay' };
    const rows = Object.keys(etiket).filter(k => dn[k] && dn[k].durum !== 'veri yok').map(k => {
      const x = dn[k];
      const is = v => `<span style="color:${v > 0 ? 'var(--up)' : v < 0 ? 'var(--down)' : 'var(--tx2)'}">${v > 0 ? '+' : ''}${v}%</span>`;
      return `<div class="lv"><span class="tp">${etiket[k]}</span><span>ons ${is(x.ons_pct)} · kur ${is(x.kur_pct)}</span><b>${is(x.gram_pct)}</b></div>` +
             (x.ons_pay != null ? `<div class="m" style="font-size:9.5px;color:var(--tx2)">katkı: ons %${x.ons_pay} · kur %${x.kur_pay}</div>` : '');
    }).join('');
    if (rows) {
      h += `<h2>⚖️ Gram Ayrışımı <span class="cnt">${alEsc(ga.formul || '')}</span></h2>` + rows;
      const kt = ga.kur_trend || {};
      h += `<div class="ict-not">Kur varsayımı: ${alEsc(ga.kur_varsayimi || '—')}` +
           (kt.aylik_kayip_pct != null ? ` · ortalama aylık değer kaybı %${kt.aylik_kayip_pct} (${kt.gun} gün)` : ' · kur trendi verisi yok') + `.</div>`;
      const gk = ga.gercek_kontrol || {};
      if (gk.sapma_pct != null) h += `<div class="ict-not">Kontrol: yaklaşık formül 21 günde gerçek gram değişiminden %${gk.sapma_pct} sapıyor (tolerans %${gk.tolerans_pct}) — ${gk.kabul ? '✅ kabul' : '❌ tolerans dışı'}.</div>`;
    }
  }

  // ── G11: KARNE (isabet) ──
  if (d.karne) {
    const kn = d.karne;
    h += `<h2>📊 Karne <span class="cnt">${kn.durum === 'ok' ? kn.kayit_sayisi + ' kayıt' : 'boş'}</span></h2>`;
    if (kn.durum !== 'ok') h += `<div class="ict-not">${alEsc(kn.not || 'veri yok')}</div>`;
    else {
      const is2 = kn.isabet || {};
      ['5g', '20g'].forEach(u => {
        const x = is2[u] || {};
        h += `<div class="lv"><span class="tp">${u === '5g' ? '5 gün' : '20 gün'} isabet</span><span>${x.ornek ? x.dogru + '/' + x.ornek : '—'}</span><b>${x.isabet_pct != null ? '%' + x.isabet_pct : 'veri yok'}</b></div>`;
      });
      h += `<div class="ict-not">Kayıtlar TR 23:00'te günde bir kez yazılır; ${alEsc(kn.ilk_tarih || '—')} → ${alEsc(kn.son_tarih || '—')}. Geçmiş uydurulmaz.</div>`;
    }
  }

  if (d.kaynak) h += `<div class="note">📐 Kaynak: ${alEsc(d.kaynak)}<br>Seviyeler salınım uçları + MA(20/50/200) + 100'lük yuvarlak seviyelerden türetilir. Senaryo tetikleri fiyattan en az 0,5×ATR, hedefler tetikten en az 1×ATR uzakta seçilir. Bias skoru deterministiktir: fiyat-MA ilişkisi, RSI, 1 aylık performans toplanır (≥+2 BOĞA, ≤−2 AYI); 52 haftalık konum artık sayılmaz. Makro skor ayrı izlenir (reel faiz, DXY, dot plot, Brent). Yatırım tavsiyesi değildir.</div>`;
  sec.innerHTML = h;
}

async function altinYukle(force) {
  const sec = document.getElementById('sec-altin');
  if (ALTIN_VERI && !force) { renderAltin(ALTIN_VERI); return; }
  sec.innerHTML = '<div class="empty">Altın verisi yükleniyor…</div>';
  try { ALTIN_VERI = await (await fetch('data/altin.json?v=' + Date.now())).json(); renderAltin(ALTIN_VERI); BAYAT.altin = utcTarih(ALTIN_VERI.uretildi); bayatBantGuncelle(); }
  catch (e) { sec.innerHTML = '<div class="empty">Altın verisi yüklenemedi: ' + e.message + '</div>'; }
}

/* ── ZİYARETÇİ GÖSTERGESİ ──
   Tamamen yerel/dekoratif. Ağ isteği, çerez, localStorage veya dış servis YOK.
   Gösterilen sayı tarihe göre deterministik üretilir (herkes aynı gün aynı sayıyı görür). */
const ZY_TABAN = 121;        // günlük gösterilen taban (patron: "121 yap")
const ZY_YAYILIM = 6;        // güne göre 0..5 sapma → günlük 121..126
const ZY_EPOK = Date.UTC(2026, 0, 1);
function zyHash(s){ let h = 2166136261 >>> 0; for (let i = 0; i < s.length; i++){ h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return h >>> 0; }
function zyYukle(){
  const d = new Date();
  const gunK = d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
  const bugun = ZY_TABAN + (zyHash(gunK) % ZY_YAYILIM);
  const gecenGun = Math.max(0, Math.floor((Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) - ZY_EPOK) / 864e5));
  const toplam = 480 + gecenGun * 57 + (zyHash('top' + gunK) % 23);
  const elB = document.getElementById('zyBugun'), elT = document.getElementById('zyToplam');
  if (elB) elB.textContent = bugun.toLocaleString('tr-TR');
  if (elT) elT.textContent = toplam.toLocaleString('tr-TR');
}

/* ── GERİYE DÖNÜK UYUMLULUK ──
   inline onclick/onchange nitelikleri ve core sekme yönetimi fonksiyonlara
   isimle erişir. Modül kapsamı global olmadığı için burada window'a bağlanır.
   Bölünen bölümler (piyasa/grafik/karne) kendi window bağlarını kurar; burada
   yalnızca bu dosyada kalan fonksiyonlar ve core yardımcıları bağlanır.
   NOT: `import * as core` ile bağlamak YANLIŞ — modül namespace nesnesinin
   değerleri salt-okunur erişimci olur, window.fmt çağrılamaz hale gelir
   (core'dan açık import + tek tek bağlama şart). */
Object.assign(window, {
  utcTarih, fmt, yuzde, ok, tazelik, BAYAT, haftaIciIsGunu, bayatBantMetni,
  bayatBantGuncelle, alEsc, pfOk, pfRenk,
  yukle, zamanGecmis,
  haberFiltrele, chip, renderHaber, renderFon, getiriYukle, durumEtiket, takvimYukle,
  krFiyat, krBuyuk, renderKripto, kriptoYukle, ictListe, renderIct, ictYukle,
  renderAltin, altinYukle, zyYukle,
});

/* ── BAŞLATMA ── */
function init() {
  sekmeKur();
  zyYukle();

  yukle();
  kriptoYukle(); // kripto 24/7 — açılışta bir kez, sekme tıklanınca ve 15 dk'da bir tazelenir
  altinYukle();  // altın — açılışta bir kez (sekme arka planda hazır olsun)
  setInterval(yukle, 900000); // 15 dk'da bir tazele
  setInterval(kriptoYukle, 900000);
  setInterval(() => altinYukle(true), 900000);
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
}

init();
