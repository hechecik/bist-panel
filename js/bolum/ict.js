/* js/bolum/ict.js — ICT Tarayıcı bölümü (G06 parça 4)
   renderIct + ictYukle + ictListe/ictYon. Veri kaynağı piyasa.json'daki
   ict_tarama bloğu; sekme ilk açılışta piyasa.json'u kendisi çeker.
   PIYASA_VERI'yi piyasa.js'ten import ETMİYORUZ — oradaki değişken
   piyasa modülünün kendi yeniden-render'ları için; ICT kendi fetch'ini
   yapar (taşımadan önceki davranışla aynı). */
import { fmt, ok } from '../core.js';

let PIYASA_VERI = null;   // ICT'nin kendi çektiği piyasa.json (piyasa.js'teki değişkenden ayrı)

/* ── ICT TARAYICI (Katman 2 — PineScript→Python mantığı) ── */
export function ictListe(baslik, ikon, items, satirFn) {
  if (!items || !items.length) return '';
  let h = `<h2>${ikon} ${baslik} <span class="cnt">${items.length}</span></h2><div class="ict-list">`;
  items.forEach(x => { h += `<div class="ict-row">${satirFn(x)}</div>`; });
  return h + '</div>';
}
export const ictYon = y => `<span class="tag ${y === 'BULLISH' ? 'up' : 'dn'}">${y === 'BULLISH' ? '▲ ALIŞ' : '▼ SATIŞ'}</span>`;

export function renderIct(d) {
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

export async function ictYukle() {
  const sec = document.getElementById('sec-ict');
  if (!PIYASA_VERI) {
    sec.innerHTML = '<div class="empty">Veri yükleniyor…</div>';
    try { PIYASA_VERI = await (await fetch('data/piyasa.json?v=' + Date.now())).json(); }
    catch (e) { sec.innerHTML = '<div class="empty">Veri yüklenemedi: ' + e.message + '</div>'; return; }
  }
  renderIct(PIYASA_VERI);
}

/* ── window bağları ── */
Object.assign(window, { ictListe, ictYon, renderIct, ictYukle });
