/* js/bolum/altin-makro.js — Altın makro sürücüler + FOMC sayacı + dot plot (G10)
   renderAltin'den ayrıldı (G06 parça 4): altin.js < 15 KB kalsın diye.
   altinMakroHtml(d) yalnızca HTML parçası döndürür; kendi try/catch'i var,
   düşerse altın bölümünün diğer blokları normal çalışır (davranış aynı). */
import { fmt, alEsc } from '../core.js';

export function altinMakroHtml(d) {
  let mh = '';
  // MAKRO SÜRÜCÜLER + FOMC SAYACI (G10) — kendi try/catch'i, düşerse diğer bloklar sürer
  try {
    const mk = d.makro || {};
    const fomc = mk.fomc || {};
    if (fomc.metin) {
      const sepB = fomc.sep ? '<span class="badge hi">SEP VAR</span>' : '<span class="badge mi">SEP YOK</span>';
      mh += `<h2>🏛️ FOMC Sayacı</h2><div class="scn"><div class="sc wide">` +
           `<div class="t">${sepB} SONRAKİ KARAR</div>` +
           `<div class="o" style="font-size:15px">${alEsc(fomc.tarih)} · ${alEsc(fomc.saat_tsi)} TSİ</div>` +
           `<div class="m"><b>${fomc.kalan_gun} gün</b> kaldı · ${alEsc(fomc.metin)}</div></div></div>`;
      if ((fomc.sonraki_liste || []).length > 1) {
        mh += '<div class="scn" style="margin-top:6px">';
        fomc.sonraki_liste.slice(0, 5).forEach(x => {
          mh += `<div class="sc"><div class="t">${alEsc(x.tarih)} ${x.sep ? '· SEP' : ''}</div>` +
               `<div class="o" style="font-size:13px">${alEsc(x.tsi)} TSİ</div></div>`;
        });
        mh += '</div>';
      }
    }

    if (mk.durum === 'veri yok') {
      mh += '<h2>🌐 Makro Sürücüler</h2><div class="scn"><div class="sc wide"><div class="t">MAKRO</div>' +
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
      mh += '<h2>🌐 Makro Sürücüler <span class="cnt">ons ile 60g korelasyon</span></h2><div class="al-lv">';
      mh += '<div class="box"><h3>💰 Dolar & Petrol</h3>' +
           satir('DXY (dolar endeksi)', py.dxy) + satir('Brent ($/varil)', py.brent) + '</div>';
      mh += '<div class="box"><h3>📉 ABD Faiz & Enflasyon</h3>' +
           satir('Reel 10Y (TIPS)', sr.DFII10, true) + satir('10Y nominal', sr.DGS10, true) +
           satir('2Y', sr.DGS2, true) + satir('10Y başabaş', sr.T10YIE, true) + '</div>';
      mh += '</div>';
      if (py.brent && py.brent.not) mh += `<div class="ict-not">🛢️ ${alEsc(py.brent.not)} Reel 10Y altının 1 numaralı makro sürücüsüdür; r değeri son 60 işlem gününün korelasyonudur.</div>`;
      if (mk.fed_bandi && mk.fed_bandi.ust != null) {
        mh += `<div class="ict-not">🏦 Fed politika faizi bandı: <b>%${fmt(mk.fed_bandi.alt)} – %${fmt(mk.fed_bandi.ust)}</b> (FRED DFEDTARL/U, ${alEsc(mk.fed_bandi.tarih)}).</div>`;
      }
    }

    const dp = mk.dot_plot || {};
    if (!dp.durum) {
      const medSir = Object.entries(dp.medyan || {}).filter(([y]) => +y >= new Date().getFullYear());
      const ima = dp.piyasa_ima || {};
      const imaYil = ima.yillar || {};
      const makasRenk = dp.makas_bp == null ? 'var(--tx2)' : dp.makas_bp > 25 ? 'var(--down)' : dp.makas_bp < -25 ? 'var(--up)' : 'var(--warn)';
      mh += '<h2>🎯 Dot Plot · Piyasa vs Fed</h2><div class="scn">';
      mh += `<div class="sc"><div class="t">DOT PLOT MEDYANI (SEP)</div><div class="o" style="font-size:13px">` +
           (medSir.length ? medSir.map(([y, v]) => `${y}: <b>%${fmt(v, 2)}</b>`).join(' · ') : 'veri yok') +
           `</div><div class="m">Kaynak: FRED FEDTARMD (FOMC SEP medyan fed funds)</div></div>`;
      mh += `<div class="sc"><div class="t">PİYASA İMA PATİKASI ${ima.kaynak === 'proxy' ? '<span class="badge mi">PROXY</span>' : '<span class="badge hi">VADELİ</span>'}</div>` +
           `<div class="o" style="font-size:13px">` +
           (Object.keys(imaYil).length ? Object.entries(imaYil).filter(([y]) => +y <= new Date().getFullYear() + 1).map(([y, v]) => `${y}: <b>%${fmt(v, 2)}</b>`).join(' · ') : 'veri yok') +
           `</div><div class="m">${ima.kaynak === 'proxy' ? alEsc(ima.not || 'proxy') : 'ZQ fed funds vadelileri · ima faiz = 100 − fiyat'}</div></div>`;
      mh += `<div class="sc"><div class="t">MAKAS · piyasa − dot${dp.makas_yil ? ' (' + dp.makas_yil + ')' : ''}</div>` +
           `<div class="o" style="color:${makasRenk}">${dp.makas_bp == null ? '—' : (dp.makas_bp > 0 ? '+' : '') + dp.makas_bp + ' bp'}</div>` +
           `<div class="m">${alEsc(dp.yorum || 'veri yok')}</div></div>`;
      mh += `<div class="sc"><div class="t">SEP REVİZYONU${dp.revizyon_yil ? ' (' + dp.revizyon_yil + ')' : ''}</div>` +
           (dp.revizyon && dp.revizyon.degisim_bp != null
             ? `<div class="o" style="color:${dp.revizyon.degisim_bp > 0 ? 'var(--down)' : dp.revizyon.degisim_bp < 0 ? 'var(--up)' : 'var(--tx2)'}">${dp.revizyon.degisim_bp > 0 ? '+' : ''}${dp.revizyon.degisim_bp} bp</div>` +
               `<div class="m">${alEsc(dp.revizyon.yorum)} · önceki SEP ${alEsc(dp.onceki_sep_tarihi || '—')} → ${alEsc(dp.sep_tarihi || '—')}</div>`
             : `<div class="o">veri yok</div><div class="m">Arşivde önceki SEP yok — ilk SEP kaydı bu çalıştırmada yazıldı${dp.sep_tarihi ? ' (' + alEsc(dp.sep_tarihi) + ')' : ''}.</div>`) +
           `</div>`;
      mh += '</div>';
      mh += '<div class="ict-not">🎯 +25 bp üstü = piyasa Fed’den şahin, −25 bp altı = güvercin, arada = uyumlu. Hiçbir faiz/olasılık/hedef değeri elle girilmez; SEP revizyonu data/sep_arsiv.json içindeki önceki SEP medyanıyla karşılaştırılarak hesaplanır.</div>';
    }
  } catch (e) {
    mh += '<h2>🌐 Makro Sürücüler</h2><div class="scn"><div class="sc wide"><div class="t">MAKRO</div><div class="o">veri yok</div><div class="m">Makro bloğu yüklenemedi — altın sayfasının diğer blokları normal çalışıyor.</div></div></div>';
  }
  return mh;
}
