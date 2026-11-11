/* js/bolum/karne-risk.js — Risk/Pozisyon Hesaplayıcı (G06 parça 4 bölme)
   karne.js 15 KB sınırını aştığı için ayrıldı: riskHesapKur, riskDoldur,
   riskStopYuzde, riskHesapla + KARNE_KURULDU bayrağı.
   Davranış birebir eski karne.js ile aynı; window bağları dosya sonunda. */
import { fmt, ok } from '../core.js';
/* ══════════ KARNE — Risk/Pozisyon Hesaplayıcı + Sinyal Karnesi ══════════ */
let KARNE_KURULDU = false;

function riskHesapKur(d) {
  const el = document.getElementById('karne-hesap');
  if (!el || KARNE_KURULDU) return;
  const s = d.sinyaller || {};
  const liste = [].concat(s.al || [], s.sat || [], s.tut || []);
  window.__RISK = liste;
  const opt = liste.map(x => `<option value="${x.sembol}">${x.sembol} · ${fmt(x.fiyat)} TL · ${(x.sinyal||'').replace('DİKKAT_','')}</option>`).join('');
  el.innerHTML =
    '<h2>🧮 Risk / Pozisyon Hesaplayıcı <span class="cnt">kaç lot · ne kadar risk</span></h2>' +
    '<div class="portfoy" style="margin-top:0">' +
      '<div class="top"><span style="font-size:12px;color:var(--tx2)">Sermaye (TL)</span>' +
        '<input id="rhSermaye" type="number" value="100000" min="0" step="1000" oninput="riskHesapla()" style="width:100px">' +
        '<span style="font-size:12px;color:var(--tx2)">Risk %</span>' +
        '<input id="rhRisk" type="number" value="1.5" min="0.1" max="10" step="0.1" oninput="riskHesapla()" style="width:64px">' +
        '<span style="font-size:12px;color:var(--tx2)">Stop %</span>' +
        '<input id="rhStopYuzde" type="number" value="8" min="0.5" max="50" step="0.5" oninput="riskStopYuzde()" style="width:64px"></div>' +
      '<div class="top"><select id="rhSembol" onchange="riskDoldur()" style="background:var(--bg3);border:1px solid var(--bd);color:var(--tx);border-radius:8px;padding:6px 9px;font-size:12px;flex:1;min-width:150px">' +
        '<option value="">— sinyalden hisse seç —</option>' + opt + '</select></div>' +
      '<div class="top"><span style="font-size:12px;color:var(--tx2)">Giriş</span>' +
        '<input id="rhGiris" type="number" step="0.01" oninput="riskHesapla()" style="width:90px">' +
        '<span style="font-size:12px;color:var(--tx2)">Stop</span>' +
        '<input id="rhStop" type="number" step="0.01" oninput="riskHesapla()" style="width:90px"></div>' +
      '<div id="rhSonuc" style="margin-top:10px"></div>' +
    '</div>';
  KARNE_KURULDU = true;
  riskHesapla();
}

function riskDoldur() {
  const sel = document.getElementById('rhSembol');
  const s = (window.__RISK || []).find(x => x.sembol === sel.value);
  if (!s) return;
  const st = s.stop != null ? s.stop : Math.round(s.fiyat * 0.92 * 100) / 100;
  document.getElementById('rhGiris').value = s.fiyat;
  document.getElementById('rhStop').value = st;
  document.getElementById('rhStopYuzde').value = Math.round(Math.abs(s.fiyat - st) / s.fiyat * 1000) / 10;
  riskHesapla();
}

function riskStopYuzde() {
  const g = +document.getElementById('rhGiris').value || 0;
  const y = +document.getElementById('rhStopYuzde').value || 0;
  if (!g) return;
  document.getElementById('rhStop').value = Math.round(g * (1 - y / 100) * 100) / 100;
  riskHesapla();
}

function riskHesapla() {
  const S = +document.getElementById('rhSermaye').value || 0;
  const r = +document.getElementById('rhRisk').value || 0;
  const G = +document.getElementById('rhGiris').value || 0;
  const St = +document.getElementById('rhStop').value || 0;
  const out = document.getElementById('rhSonuc');
  if (!out) return;
  if (!S || !G || !St || G === St) { out.innerHTML = '<div class="note">Sermaye, giriş ve stop gir — ya da yukarıdan sinyal seç.</div>'; return; }
  const riskTL = S * r / 100, mesafe = Math.abs(G - St), mesafeY = mesafe / G * 100;
  const lot = Math.floor(riskTL / mesafe), pozTL = lot * G, pozY = pozTL / S * 100;
  const long = G > St, yon = long ? 'LONG' : 'SHORT';
  const hedef = k => long ? G + k * mesafe : G - k * mesafe;
  const asiri = pozTL > S;
  out.innerHTML =
    '<div class="scn">' +
      `<div class="sc"><div class="t">Riske Edilen</div><div class="o down">${fmt(riskTL,0)} TL</div><div class="m">sermayenin %${r}</div></div>` +
      `<div class="sc"><div class="t">Alınacak Lot</div><div class="o">${fmt(lot,0)}</div><div class="m">${yon} · stop %${mesafeY.toFixed(1)}</div></div>` +
      `<div class="sc"><div class="t">Pozisyon Tutarı</div><div class="o"${asiri?' style="color:var(--warn)"':''}>${fmt(pozTL,0)} TL</div><div class="m">sermayenin %${pozY.toFixed(0)}</div></div>` +
      `<div class="sc"><div class="t">Lot Başı Risk</div><div class="o">${fmt(mesafe,2)} TL</div><div class="m">giriş − stop</div></div>` +
    '</div>' +
    '<div class="twrap"><table><tr><th>Hedef</th><th>Fiyat</th><th>Kâr</th><th>R:R</th></tr><tbody>' +
      [1,2,3].map(k => `<tr><td>${k}R</td><td class="sym">${fmt(hedef(k))}</td><td class="up">+${fmt(lot*(hedef(k)-G),0)} TL</td><td>1:${k}</td></tr>`).join('') +
    '</tbody></table></div>' +
    `<div class="note">Lot = (Sermaye × Risk%) ÷ |Giriş − Stop|. Giriş ${fmt(G)} · Stop ${fmt(St)}. ` +
    (asiri ? '⚠️ Pozisyon sermayeni aşıyor — stop\'u sık veya risk yüzdesini düşür.' : 'Pozisyon sermaye içinde ✓') + '</div>';
}

/* ── window bağları ── */
Object.assign(window, { riskHesapKur, riskDoldur, riskStopYuzde, riskHesapla });
