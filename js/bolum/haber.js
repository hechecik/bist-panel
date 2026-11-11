/* js/bolum/haber.js — HABER bölümü (G06 parça 3)
   renderHaber + kategori/dil/yön filtreleri + "kaç dk önce" damgası.
   Haber bölümündeki Aşırı Satım/Alım taraması ve mini takvim de burada. */
import { fmt, utcTarih } from '../core.js';

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

export function renderHaber(d) {
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

window.haberFiltrele = haberFiltrele;
window.chip = chip;
window.renderHaber = renderHaber;
window.zamanGecmis = zamanGecmis;
