/* main.js — giriş noktası (G06 parça 2)
   index.html'de yalnızca iskelet ve <script type="module" src="js/main.js">
   kalır. Bu dosya core'u ve bölüm modüllerini içe alır, onları window'a bağlar
   (inline onclick/onchange ve sekme yönetimi için), sekmeleri kurar ve başlatır.

   Taşınanlar (parça 2): piyasa + filtre/portföy/alarm → js/bolum/piyasa.js,
   grafik/mum modalı → js/bolum/grafik.js, karne/senaryo → js/bolum/karne.js.
   Taşınanlar (parça 3): haber → js/bolum/haber.js, fon → js/bolum/fon.js,
   getiri/takvim → js/bolum/getiri.js + takvim.js.
   Taşınanlar (parça 4): kripto → js/bolum/kripto.js, ICT → js/bolum/ict.js,
   altın → js/bolum/altin.js (+ makro/FOMC bloğu → altin-makro.js).
   Bu dosya artık yalnızca import + başlatma yapar. */
import { utcTarih, fmt, yuzde, ok, tazelik, BAYAT, haftaIciIsGunu, bayatBantMetni,
         bayatBantGuncelle, alEsc, pfOk, pfRenk, sekmeKur } from './core.js';
import { renderPiyasa, alarmKontrol, durum } from './bolum/piyasa.js';
import { renderGrafik } from './bolum/grafik.js';
import { renderSenaryo } from './bolum/karne.js';
import { renderHaber } from './bolum/haber.js';
import { renderFon } from './bolum/fon.js';
import { getiriYukle } from './bolum/getiri.js';
import { takvimYukle } from './bolum/takvim.js';
import { krFiyat, krBuyuk, renderKripto, kriptoYukle } from './bolum/kripto.js';
import { ictListe, renderIct, ictYukle } from './bolum/ict.js';
import { renderAltin, altinYukle } from './bolum/altin.js';

async function yukle() {
  try {
    const d = await (await fetch('data/piyasa.json?v=' + Date.now())).json();
    durum.hesapTarihi = (d.sinyaller && d.sinyaller.hesap_tarihi) || '';
    /* G06: detay satırı veriye bağlandı — sembol → sinyal kaydı.
       Alanlar: Tüm Nedenler, Seviyeler (S1/R1/stop/hedef), Veri, G05 Filtre. */
    durum.detay = new Map();
    for (const grup of ['al', 'tut', 'sat', 'izle', 'riskli'])
      for (const r of ((d.sinyaller && d.sinyaller[grup]) || []))
        if (r && r.sembol) durum.detay.set(r.sembol, r);
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
   Bölünen bölümler (piyasa/grafik/karne/haber/fon/getiri/takvim) kendi window bağlarını kurar; burada
   yalnızca bu dosyada kalan fonksiyonlar ve core yardımcıları bağlanır.
   NOT: `import * as core` ile bağlamak YANLIŞ — modül namespace nesnesinin
   değerleri salt-okunur erişimci olur, window.fmt çağrılamaz hale gelir
   (core'dan açık import + tek tek bağlama şart). */
Object.assign(window, {
  utcTarih, fmt, yuzde, ok, tazelik, BAYAT, haftaIciIsGunu, bayatBantMetni,
  bayatBantGuncelle, alEsc, pfOk, pfRenk,
  yukle, renderHaber, renderFon, getiriYukle, takvimYukle,
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
