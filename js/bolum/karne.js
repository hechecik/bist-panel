/* js/bolum/karne.js — KARNE bölümü (G06 parça 2, parça 4'te bölündü)
   Sinyal performans karnesi (karnePerformans) ve renderSenaryo.
   Risk/pozisyon hesaplayıcı bu boyut sınırı nedeniyle karne-risk.js'e taşındı;
   o dosyanın fonksiyonları window üzerinden erişilir (inline onclick).
   Davranış birebir eski main.js ile aynı; window bağları dosya sonunda. */
import { fmt, yuzde, ok } from '../core.js';
import './karne-risk.js';

function karnePerformans(d) {
  const sg = d.sinyal_gecmisi;
  if (!sg || !sg.kayitlar || !sg.kayitlar.length)
    return '<h2>🎯 Sinyal Performans Karnesi</h2><div class="empty">Karne veri topluyor — sinyal geçmişi biriktikçe başarı ve ortalama getiri burada görünecek.</div>';
  const k = sg.kayitlar, get = x => x.getiri == null ? 0 : x.getiri;
  const poz = k.filter(x => get(x) > 0).length, neg = k.filter(x => get(x) < 0).length;
  const ort = k.reduce((a, x) => a + get(x), 0) / k.length;
  const sirali = [...k].sort((a, b) => get(b) - get(a));
  const enIyi = sirali[0], enKotu = sirali[sirali.length - 1];
  const alt = k.filter(x => (x.sinyal || '').includes('AL')), satL = k.filter(x => (x.sinyal || '').includes('SAT'));
  const oo = a => a.length ? a.reduce((s, x) => s + get(x), 0) / a.length : null;
  const bo = a => a.length ? Math.round(a.filter(x => get(x) > 0).length / a.length * 100) : null;
  const oran = Math.round(poz / k.length * 100);
  const renk = ort >= 0 ? 'var(--up)' : 'var(--down)';
  let h = '<h2>🎯 Sinyal Performans Karnesi <span class="cnt">' + k.length + ' sinyal · %' + (sg.basari_orani ?? oran) + ' başarı</span></h2>' +
    '<div class="scn">' +
      `<div class="sc"><div class="t">Başarı Oranı</div><div class="o" style="color:${renk}">%${sg.basari_orani ?? oran}</div><div class="m">🟢 ${poz} · 🔴 ${neg}</div></div>` +
      `<div class="sc"><div class="t">Ort. Getiri</div><div class="o" style="color:${renk}">${ort >= 0 ? '+' : ''}%${ort.toFixed(2)}</div><div class="m">sinyal başına</div></div>` +
      `<div class="sc"><div class="t">En İyi Sinyal</div><div class="o up">${enIyi.sembol}</div><div class="m">+%${get(enIyi).toFixed(1)} · ${enIyi.tarih}</div></div>` +
      `<div class="sc"><div class="t">En Kötü Sinyal</div><div class="o down">${enKotu.sembol}</div><div class="m">%${get(enKotu).toFixed(1)} · ${enKotu.tarih}</div></div>` +
    '</div>' +
    '<div class="twrap"><table><tr><th>Sinyal</th><th>Adet</th><th>Başarı</th><th>Ort. Getiri</th></tr><tbody>' +
      `<tr><td class="sym">AL</td><td>${alt.length}</td><td>${bo(alt) == null ? '—' : '%' + bo(alt)}</td><td class="${ok(oo(alt))}">${oo(alt) == null ? '—' : (oo(alt) >= 0 ? '+' : '') + '%' + oo(alt).toFixed(2)}</td></tr>` +
      `<tr><td class="sym">SAT</td><td>${satL.length}</td><td>${bo(satL) == null ? '—' : '%' + bo(satL)}</td><td class="${ok(oo(satL))}">${oo(satL) == null ? '—' : (oo(satL) >= 0 ? '+' : '') + '%' + oo(satL).toFixed(2)}</td></tr>` +
    '</tbody></table></div>' +
    '<h2>📋 Son Sinyaller</h2><div class="twrap"><table><tr><th>Tarih</th><th>Hisse</th><th>Sinyal</th><th>Skor</th><th>Giriş</th><th>Güncel</th><th>Getiri</th></tr><tbody>';
  [...k].reverse().slice(0, 15).forEach(x => {
    h += `<tr><td>${x.tarih || ''}</td><td class="sym">${x.sembol}</td><td>${window.badge(x.sinyal)}</td>` +
      `<td style="color:${x.skor >= 3 ? 'var(--up)' : x.skor <= -3 ? 'var(--down)' : 'var(--warn)'}">${x.skor > 0 ? '+' : ''}${x.skor}</td>` +
      `<td>${fmt(x.giris)}</td><td>${x.guncel == null ? '—' : fmt(x.guncel)}</td>` +
      `<td class="${ok(x.getiri)}">${x.getiri == null ? '—' : yuzde(x.getiri)}</td></tr>`;
  });
  h += '</tbody></table></div><div class="note">Getiri = sinyal günü kapanış → bugünkü fiyat. Gerçek veri; sinyal sayısı arttıkça karne anlam kazanır.</div>';
  return h;
}

export function renderSenaryo(d) {
  riskHesapKur(d);
  const t = d.test_senaryolari;
  let html = karnePerformans(d);
  if (t) {
    html += '<h2>🧪 Simülasyon — 6 Aylık Gerçek Veri · 💵 100K TL</h2><div class="scn">';
    const karti = (s, sermaye, acik) => {
      if (!s) return;
      const renk = s.ortalama >= 0 ? 'var(--up)' : 'var(--down)';
      const poz = Math.max(0, Math.min(100, 50 + s.ortalama * 2));
      const basari = s.islem ? Math.round(s.kazanan / s.islem * 100) : 0;
      const kb = s.islem ? `<div class="bar"><i style="width:${basari}%;background:var(--up)"></i><i style="width:${100-basari}%;background:var(--down)"></i></div>` : '';
      const tl = sermaye ? `<div class="m">💵 <b>100K TL ile: ${fmt(sermaye.sonuc,0)} TL</b> <span class="${ok(sermaye.kar_zarar)}">(${sermaye.kar_zarar >= 0 ? '+' : ''}${fmt(sermaye.kar_zarar,0)} TL)</span> · ${fmt(sermaye.tahsis,0)} TL/pozisyon</div>` : '';
      html += `<div class="sc ${acik?'wide':''}"><div class="t">${s.ad}</div>` +
        `<div class="o" style="color:${renk}">${s.ortalama >= 0 ? '+' : ''}%${s.ortalama.toFixed(1)}</div>` +
        `<div class="bar"><i style="width:${poz}%;background:${s.ortalama>=0?'var(--up)':'var(--down)'}"></i></div>` +
        `<div class="m">${s.islem} işlem · 🟢 ${s.kazanan} · 🔴 ${s.kaybeden} · <b>%${basari} başarı</b></div>` + kb + tl;
      if (s.en_iyi) html += `<div class="m">🏆 ${s.en_iyi.sembol} %${s.en_iyi.getiri_yuzde >= 0 ? '+' : ''}${s.en_iyi.getiri_yuzde} (${s.en_iyi.tarih})</div>`;
      if (s.en_kotu) html += `<div class="m">💀 ${s.en_kotu.sembol} %${s.en_kotu.getiri_yuzde >= 0 ? '+' : ''}${s.en_kotu.getiri_yuzde} (${s.en_kotu.tarih})</div>`;
      html += '</div>';
    };
    const sm = t.sermaye || {};
    karti(t.pazartesi_acilis, sm.pazartesi);
    karti(t.ertesi_gun_acilis, sm.ertesi);
    karti(t.stop_losslu, sm.stop, true);
    html += '</div><div class="note">' + (t.aciklama || '') + '</div>';

    // G08 — XU100'e göre alfa + işlem metrikleri (eski alanlar üstte korunuyor)
    if (t.metrik) {
      const m = t.metrik;
      const af = v => v == null ? '—' : (v >= 0 ? '+' : '') + '%' + v.toFixed(1);
      const afK = v => v == null ? '' : (v >= 0 ? 'up' : 'down');
      html += '<h2>📐 Performans — XU100\'e göre <span class="cnt">' + m.islem + ' işlem</span></h2><div class="scn">' +
        `<div class="sc"><div class="t">Ortalama Alfa (XU100'e göre)</div><div class="o ${afK(m.ortalama_alfa)}">${af(m.ortalama_alfa)}</div><div class="m">işlem başına, endeks fazlası</div></div>` +
        `<div class="sc"><div class="t">İşlem Getirisi</div><div class="o ${m.ortalama >= 0 ? 'up' : 'down'}">${af(m.ortalama)}</div><div class="m">maliyet düşülmüş, işlem başına</div></div>` +
        `<div class="sc"><div class="t">İsabet</div><div class="o">%${m.isabet == null ? '—' : (m.isabet * 100).toFixed(1)}</div><div class="m">${m.islem} işlem</div></div>` +
        `<div class="sc"><div class="t">Profit Factor</div><div class="o ${(m.profit_factor ?? 0) >= 1 ? 'up' : 'down'}">${m.profit_factor == null ? '—' : m.profit_factor.toFixed(2)}</div><div class="m">kâr / zarar</div></div>` +
        `<div class="sc"><div class="t">Gerçekleşen Max Düşüş (100K)</div><div class="o down">${m.max_drawdown == null ? '—' : '%' + m.max_drawdown.toFixed(1)}</div><div class="m">kronolojik simülasyon, açık pozisyonlar maliyetten</div></div>` +
        `<div class="sc"><div class="t">Devir</div><div class="o">${m.devir == null ? '—' : m.devir.toFixed(0)}</div><div class="m">yıllık işlem / pozisyon</div></div>` +
        '</div>';

      if (t.skor_tablosu && t.skor_tablosu.length) {
        html += '<h2>🎚️ Skor Seviyesine Göre <span class="cnt">XU100\'e göre alfa</span></h2><div class="twrap"><table><tr>' +
          '<th>Skor</th><th>İşlem</th><th>İsabet</th><th>Ort. Getiri</th><th>Ort. Alfa (XU100\'e göre)</th><th>Profit Factor</th><th>Gerçekleşen Max DD</th></tr><tbody>';
        t.skor_tablosu.forEach(r => {
          html += `<tr><td class="sym">${r.skor}</td><td>${r.islem}</td>` +
            `<td>${r.isabet == null ? '—' : '%' + (r.isabet * 100).toFixed(1)}</td>` +
            `<td class="${r.ortalama >= 0 ? 'up' : 'down'}">${af(r.ortalama)}</td>` +
            `<td class="${afK(r.ortalama_alfa)}">${af(r.ortalama_alfa)}</td>` +
            `<td>${r.profit_factor == null ? '—' : r.profit_factor.toFixed(2)}</td>` +
            `<td class="down">${r.max_drawdown == null ? '—' : '%' + r.max_drawdown.toFixed(1)}</td></tr>`;
        });
        html += '</tbody></table></div>';
      }
      if (t.parametre) {
        const p = t.parametre;
        html += `<div class="note">Parametreler: maliyet %${(p.maliyet * 100).toFixed(2)} (gidiş-dönüş) · vade ${(p.vade_gun || []).join('/')} iş günü · stop ${p.atr_stop}×ATR · hedef ${p.atr_hedef}×ATR · ${fmt(p.sermaye, 0)} TL · max ${p.max_pozisyon} pozisyon · benchmark ${p.benchmark}</div>`;
      }
    }

    // Hisse bazlı backtest
    if (t.hisse_bazli && t.hisse_bazli.length) {
      html += '<h2>📈 Hisse Bazlı Backtest <span class="cnt">sinyal başına</span></h2><div class="twrap"><table><tr>' +
        '<th>Hisse</th><th>Toplam Getiri</th><th>İşlem</th><th>Başarı</th><th>En Kötü İşlem</th></tr><tbody>';
      t.hisse_bazli.forEach(x => {
        // en_kotu_islem yeni ad; eski 'max_dusus' bir sürüm boyunca yedek
        const ek = x.en_kotu_islem != null ? x.en_kotu_islem : x.max_dusus;
        html += `<tr><td class="sym">${x.sembol}</td>` +
          `<td class="${ok(x.toplam_getiri)}">${x.toplam_getiri >= 0 ? '+' : ''}%${x.toplam_getiri.toFixed(1)}</td>` +
          `<td>${x.islem_sayisi}</td><td>%${x.basari_orani}</td>` +
          `<td class="${ek >= 0 ? 'up' : 'down'}">${ek == null ? '—' : (ek >= 0 ? '+' : '') + '%' + ek.toFixed(1)}</td></tr>`;
      });
      html += '</tbody></table></div>';
    }

    const ilk = (t.ertesi_gun_acilis && t.ertesi_gun_acilis.islemler) || [];
    if (ilk.length) {
      // G08 — işlemler artık vade/stop/hedef ile kapanıyor: çıkış tarihi + neden gösterilir.
      // Eski alanlar (bugun, getiri_yuzde) korunur; çıkış yoksa 'Bugün' kolonuna düşülür.
      html += '<h2>🏆 En Kârlı İşlemler (son 6 ay)</h2><div class="twrap"><table><tr>' +
        '<th>Hisse</th><th>Sinyal</th><th>Giriş</th><th>Çıkış</th><th>Neden</th><th>Getiri</th>' +
        '<th title="Aynı tarihlerde XU100 getirisi düşülmüş">Alfa (XU100\'e göre)</th></tr><tbody>';
      ilk.slice(0, 10).forEach(x => {
        const cikis = x.cikis_tarih || (x.bugun != null ? 'açık' : '—');
        const neden = x.cikis_neden === 'stop' ? '🛑 stop' : x.cikis_neden === 'hedef' ? '🎯 hedef' : x.cikis_neden === 'vade' ? '⏱ vade' : '—';
        const alfa = x.alfa_yuzde == null ? '—' : (x.alfa_yuzde >= 0 ? '+' : '') + '%' + x.alfa_yuzde.toFixed(1);
        html += `<tr><td class="sym">${x.sembol}</td><td>${x.sinyal_tarih}</td><td>${fmt(x.giris)}</td>` +
          `<td>${cikis}</td><td>${neden}</td><td class="${ok(x.getiri_yuzde)}">${yuzde(x.getiri_yuzde)}</td>` +
          `<td class="${x.alfa_yuzde == null ? '' : (x.alfa_yuzde >= 0 ? 'up' : 'down')}">${alfa}</td></tr>`;
      });
      html += '</tbody></table></div>';
    }
  }
  const hedefEl = document.getElementById('karne-icerik');
  if (hedefEl) hedefEl.innerHTML = html;
}

/* ── window bağları (inline onclick/oninput/onchange için) ── */
Object.assign(window, { karnePerformans, renderSenaryo });
