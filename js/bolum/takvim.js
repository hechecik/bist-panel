/* js/bolum/takvim.js — TAKVİM bölümü (G06 parça 3)
   takvimYukle: halka arz + ertelenen/iptal + temettü (data/takvim.json). */
import { fmt } from '../core.js';

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

export async function takvimYukle() {
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

window.takvimYukle = takvimYukle;
window.durumEtiket = durumEtiket;
