// Service Worker — çevrimdışı önbellek (PWA)
const CACHE = 'bist-panel-v5';
const CORE = ['/', '/index.html', '/manifest.json',
  // G06: ön yüz bölündü — CSS ve JS ayrı dosyalar
  '/css/app.css', '/js/core.js', '/js/main.js',
  // G06 parça 2: bölüm dosyaları
  '/js/bolum/piyasa.js', '/js/bolum/grafik.js', '/js/bolum/karne.js',
  // G06 parça 3: bölüm dosyaları
  '/js/bolum/haber.js', '/js/bolum/fon.js', '/js/bolum/getiri.js', '/js/bolum/takvim.js',
  // G06 parça 4: bölüm dosyaları
  '/js/bolum/kripto.js', '/js/bolum/ict.js', '/js/bolum/altin.js', '/js/bolum/altin-makro.js',
  // G06 parça 4b: 15 KB sınırı için ayrılan yardımcı/alt bölümler
  '/js/bolum/piyasa-yardimci.js', '/js/bolum/piyasa-tablo.js', '/js/bolum/piyasa-filtre.js',
  '/js/bolum/piyasa-reel.js', '/js/bolum/karne-risk.js', '/js/bolum/portfoy.js'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // Veri JSON'ları: ağ öncelikli, düşerse önbellek (her 15 dk güncellenir)
  if (url.pathname.includes('/data/')) {
    e.respondWith(
      fetch(e.request).then(r => {
        const copy = r.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
        return r;
      }).catch(() => caches.match(e.request))
    );
    return;
  }
  // Statik: önbellek öncelikli
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request).then(resp => {
      const copy = resp.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy));
      return resp;
    }))
  );
});
