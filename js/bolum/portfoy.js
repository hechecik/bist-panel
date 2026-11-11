/* js/bolum/portfoy.js — Portföy + Fiyat Alarmları (G06 parça 4 bölme)
   piyasa.js 15 KB sınırını aştığı için ayrıldı: localStorage portföyü,
   hedef/stop alarmları, bildirimler. PIYASA_VERI'yi piyasa.js'ten CANLI
   binding olarak import eder (tek kaynak, kopya yok).
   Davranış birebir eski piyasa.js ile aynı; window bağları dosya sonunda. */
import { fmt, alEsc, pfOk, pfRenk } from '../core.js';
import { PIYASA_VERI } from '../core.js';

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

/* ── window bağları ── */
Object.assign(window, { portfoyOku, portfoyKaydet, fiyatBul, bildirimIzni, bildirim, portfoyHtml, portfoyEkle, portfoySil, alarmSifirla, alarmKontrol });
