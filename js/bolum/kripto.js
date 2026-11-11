/* js/bolum/kripto.js — Kripto bölümü (G06 parça 4)
   renderKripto + kriptoYukle + krFiyat/krBuyuk yardımcıları.
   Icon inline onclick yok; sekme yönetimi (core.sekmeKur) kriptoYukle'yi
   window üzerinden çağırır. */
import { fmt, yuzde, ok } from '../core.js';
import { badge, sparkSVG } from './piyasa-yardimci.js';

let KRIPTO_VERI = null;

// fiyat kısaltma: coin başına anlamlı hassasiyet (BTC 82.508,00 / SHIB 0,0000123)
export function krFiyat(n) {
  if (n == null) return '—';
  const a = Math.abs(n);
  const h = a >= 1000 ? 2 : a >= 1 ? 2 : a >= 0.01 ? 4 : 8;
  return Number(n).toLocaleString('tr-TR', {minimumFractionDigits: h, maximumFractionDigits: h});
}
// büyük sayı kısaltma: 2,91 T / 139,4 Mr
export function krBuyuk(n) {
  if (n == null) return '—';
  const a = Math.abs(n);
  if (a >= 1e12) return fmt(n / 1e12, 2) + ' T';
  if (a >= 1e9) return fmt(n / 1e9, 1) + ' Mr';
  if (a >= 1e6) return fmt(n / 1e6, 1) + ' M';
  return fmt(n, 0);
}

export function renderKripto(d) {
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

export async function kriptoYukle() {
  const sec = document.getElementById('sec-kripto');
  if (!KRIPTO_VERI) sec.innerHTML = '<div class="empty">Kripto verisi yükleniyor…</div>';
  try {
    const d = await (await fetch('data/kripto.json?v=' + Date.now())).json();
    renderKripto(d);
  } catch (e) {
    if (!KRIPTO_VERI) sec.innerHTML = '<div class="empty">Kripto verisi yüklenemedi: ' + e.message + '</div>';
  }
}

/* ── window bağları (sekme yönetimi + geriye dönük uyumluluk) ── */
Object.assign(window, { krFiyat, krBuyuk, renderKripto, kriptoYukle });
