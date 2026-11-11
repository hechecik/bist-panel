/* js/bolum/altin.js — Ons Altın bölümü (G06 parça 4)
   renderAltin + altinYukle. Vitaller, seviyeler, senaryo, makro sürücüler,
   FOMC sayacı + dot plot (G10), skor ayrımı / 4 senaryo / gram ayrışımı /
   karne (G11) bloklarının hepsi burada. Makro bloğu kendi try/catch'inde. */
import { utcTarih, fmt, BAYAT, bayatBantGuncelle, alEsc, pfOk, pfRenk } from '../core.js';
import { altinMakroHtml } from './altin-makro.js';

/* ── ALTIN (ONS) BÖLÜMÜ ── */
let ALTIN_VERI = null;
export function renderAltin(d) {
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

  // MAKRO SÜRÜCÜLER + FOMC SAYACI + DOT PLOT (G10) — altin-makro.js'te, kendi try/catch'i var
  h += altinMakroHtml(d);

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

export async function altinYukle(force) {
  const sec = document.getElementById('sec-altin');
  if (ALTIN_VERI && !force) { renderAltin(ALTIN_VERI); return; }
  sec.innerHTML = '<div class="empty">Altın verisi yükleniyor…</div>';
  try { ALTIN_VERI = await (await fetch('data/altin.json?v=' + Date.now())).json(); renderAltin(ALTIN_VERI); BAYAT.altin = utcTarih(ALTIN_VERI.uretildi); bayatBantGuncelle(); }
  catch (e) { sec.innerHTML = '<div class="empty">Altın verisi yüklenemedi: ' + e.message + '</div>'; }
}

/* ── window bağları ── */
Object.assign(window, { renderAltin, altinYukle });
