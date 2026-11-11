import { KOLONLAR, hisseSatir, tabloBolum } from './piyasa-tablo.js';
import { durum, PIYASA_VERI } from '../core.js';

/* ══════════ FİLTRE / CSV ══════════ */
/* ══════════ FİLTRE ══════════ */
export function filtrele() {
  const q = (document.getElementById('arama').value || '').toUpperCase().trim();
  const fs = document.getElementById('fSinyal').value;
  const ft = document.getElementById('fTrend').value;
  const fq = document.getElementById('fSqueeze').value;
  document.querySelectorAll('#sec-piyasa tbody tr[data-sym]').forEach(tr => {
    const sym = tr.dataset.sym;
    const r = PIYASA_VERI && [...(PIYASA_VERI.sinyaller.al||[]), ...(PIYASA_VERI.sinyaller.tut||[]), ...(PIYASA_VERI.sinyaller.sat||[]), ...(PIYASA_VERI.sinyaller.izle||[]), ...(PIYASA_VERI.sinyaller.riskli||[])].find(x => x.sembol === sym);
    if (!r) return;
    const okS = !fs || r.sinyal === fs;
    const okT = !ft || r.trend === ft;
    const okQ = !fq || (fq === 'SIKIŞMA' ? (r.squeeze||'').toUpperCase().includes('SIKIŞMA') : (r.squeeze||'').toUpperCase().includes('KIRILIM'));
    const okA = !q || sym.includes(q);
    tr.style.display = (okS && okT && okQ && okA) ? '' : 'none';
    const det = document.querySelector(`tr.detail[data-det="${sym}"]`);
    if (det) det.style.display = 'none';
  });
}

/* ══════════ CSV ══════════ */
export function csvIndir() {
  const d = PIYASA_VERI; if (!d) return;
  const satirlar = [...(d.sinyaller.al||[]), ...(d.sinyaller.tut||[]), ...(d.sinyaller.sat||[]), ...(d.sinyaller.izle||[]), ...(d.sinyaller.riskli||[])];
  const baslik = 'Hisse,Fiyat,1A%,RS20,RS60,HacimOran,VOL20,ZirveUzak,TrendATR,Skor,Sinyal,Trend,Para,RSI,MFI,Squeeze,S1,R1,Stop,Hedef,Kilit,IpoYeni,Riskli,LikiditeTL,Filtre';
  const csv = [baslik, ...satirlar.map(r =>
    [r.sembol, r.fiyat, r.ay_oncesi ?? '', r.RS20 ?? '', r.RS60 ?? '', r.HACIM_ORAN ?? '', r.VOL20 ?? '',
     r.ZIRVE_UZAK ?? '', r.TREND_ATR ?? '', r.skor, r.sinyal, r.trend, r.para, r.rsi, r.mfi,
     r.squeeze, r.s1 ?? '', r.r1 ?? '', r.stop ?? '', r.hedef ?? '',
     r.kilit ?? '', r.ipo_yeni ? 'EVET' : '', r.riskli ?? '',
     r.likidite_tl == null ? '' : Math.round(r.likidite_tl), r.filtre ?? ''].join(','))].join('\n');
  const blob = new Blob(['\ufeff' + csv], {type:'text/csv;charset=utf-8'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'bist-panel-' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
}
