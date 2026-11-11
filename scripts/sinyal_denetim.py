#!/usr/bin/env python3
"""
Sinyal denetimi — bist-panel sinyallerinin ileriye dönük getiriyi gerçekten
ayırt edip etmediğini ölçer. Ağ bağlantısı gerektirmez.

Kaynak (iki mod):
  1) --git REPO   : data/piyasa.json'un git geçmişindeki tüm snapshot'lar
                    (sinyal listeleri + 30 günlük spark'tan fiyat paneli kurulur)
  2) --log DIZIN  : data/log/*.jsonl (tam kesit günlük kayıt — önerilen yeni format)

Çıktı: konsola rapor + --json ile makine okunur özet.
Kullanım:
  python sinyal_denetim.py --git . --ufuk 5 10
  python sinyal_denetim.py --log data/log --ufuk 5 10 20 --json rapor.json
"""
import argparse, collections, datetime as dt, json, math, os, statistics as st, subprocess

TATIL = {'2026-07-15', '2026-10-29'}          # BIST tam gün kapalı — her yıl güncelle
SICRAMA_ESIK = 0.30                            # |günlük getiri| > %30 → bölünme şüphesi, dışla


def takvim(a, b):
    d, out = dt.date.fromisoformat(a), []
    while d.isoformat() <= b:
        if d.weekday() < 5 and d.isoformat() not in TATIL:
            out.append(d.isoformat())
        d += dt.timedelta(1)
    return out


# ───────────────────────── veri yükleme ─────────────────────────
def git_snapshotlari(repo):
    out = subprocess.run(['git', '-C', repo, 'log', '--format=%H %cI', '--', 'data/piyasa.json'],
                         capture_output=True, text=True).stdout.split('\n')
    snaps = []
    for line in out:
        if not line.strip():
            continue
        h, t = line.split()
        try:
            d = json.loads(subprocess.run(['git', '-C', repo, 'show', f'{h}:data/piyasa.json'],
                                          capture_output=True, text=True).stdout)
        except Exception:
            continue
        s = d.get('sinyaller') or {}
        rows = []
        for g in ('al', 'tut', 'sat', 'tum'):
            rows += s.get(g) or []
        snaps.append({'t': t, 'endeks': d.get('endeks'), 'rows': rows})
    return sorted(snaps, key=lambda x: x['t'])


def log_snapshotlari(dizin):
    snaps = []
    for f in sorted(os.listdir(dizin)):
        if f.endswith('.jsonl'):
            for line in open(os.path.join(dizin, f), encoding='utf-8'):
                if line.strip():
                    snaps.append(json.loads(line))
    return sorted(snaps, key=lambda x: x['t'])


def panel_kur(snaps):
    tarihler = [r['tarih'] for s in snaps for r in s['rows'] if r.get('tarih')]
    cal = takvim((dt.date.fromisoformat(min(tarihler)) - dt.timedelta(60)).isoformat(),
                 (dt.date.fromisoformat(max(tarihler)) + dt.timedelta(40)).isoformat())
    idx = {d: i for i, d in enumerate(cal)}
    fiyat = collections.defaultdict(dict)
    endeks = {}
    son = {}
    for s in snaps:
        e = s.get('endeks')
        if e and e.get('tarih'):
            endeks[e['tarih']] = e['deger']
        for r in s['rows']:
            t = r.get('tarih')
            if t not in idx:
                continue
            seri = r.get('spark') or [r.get('fiyat')]
            for k, v in enumerate(reversed(seri)):
                if v:
                    fiyat[r['sembol']][cal[idx[t] - k]] = v
            son[(t, r['sembol'])] = r            # günün SON ölçümü = kapanış durumu
    return cal, idx, fiyat, endeks, son


# ───────────────────────── istatistik ─────────────────────────
def spearman(x, y):
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0] * len(v)
        for k, i in enumerate(o):
            r[i] = k
        return r
    if len(x) < 5:
        return None
    rx, ry = rank(x), rank(y)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else None


def t_stat(v):
    if len(v) < 3 or st.stdev(v) == 0:
        return float('nan')
    return st.mean(v) / (st.stdev(v) / math.sqrt(len(v)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--git'); ap.add_argument('--log')
    ap.add_argument('--ufuk', type=int, nargs='+', default=[5, 10])
    ap.add_argument('--json')
    a = ap.parse_args()
    snaps = git_snapshotlari(a.git) if a.git else log_snapshotlari(a.log)
    cal, idx, F, E, son = panel_kur(snaps)

    def fwd(sym, d, h):
        i = idx.get(d)
        if i is None or i + h >= len(cal):
            return None
        p = [F[sym].get(cal[j]) for j in range(i, i + h + 1)]
        if any(v is None for v in (p[0], p[-1])):
            return None
        for u, v in zip(p, p[1:]):                       # bölünme filtresi
            if u and v and abs(v / u - 1) > SICRAMA_ESIK:
                return None
        return p[-1] / p[0] - 1

    rapor = {'snapshot': len(snaps), 'gun': len({d for d, _ in son}), 'ufuklar': {}}
    print(f"snapshot={len(snaps)}  gözlenen gün={rapor['gun']}  sembol={len(F)}")
    if a.git:
        print("UYARI: git modunda sadece listelenen hisseler var (kırpılmış kesit) → sonuçlar yön gösterir, kanıt değildir.")
    if rapor['gun'] < 120:
        print(f"UYARI: {rapor['gun']} gün az — anlamlı karar için ≥120 işlem günü tam kesit log gerekir.\n")

    ozellikler = {
        'skor': lambda r: r.get('skor'),
        'rsi': lambda r: r.get('rsi'),
        'mfi': lambda r: r.get('mfi'),
        'macd_hist/fiyat': lambda r: (r.get('macd_hist') or 0) / r['fiyat'] if r.get('fiyat') else None,
        'ay_getirisi': lambda r: r.get('ay_oncesi'),
        # G09 — gölge mod göstergeleri (skor/sinyale GİRMEZ, sadece IC ölçümü)
        'RS20': lambda r: r.get('RS20'),
        'RS60': lambda r: r.get('RS60'),
        'HACIM_ORAN': lambda r: r.get('HACIM_ORAN'),
        'VOL20': lambda r: r.get('VOL20'),
        'ZIRVE_UZAK': lambda r: r.get('ZIRVE_UZAK'),
        'TREND_ATR': lambda r: r.get('TREND_ATR'),
    }
    for h in a.ufuk:
        gunluk = collections.defaultdict(list)
        for (d, sym), r in son.items():
            f = fwd(sym, d, h)
            if f is not None:
                gunluk[d].append((r, f))
        gunler = sorted(gunluk)
        res = {}
        print(f"══ UFUK {h} iş günü ══  (gün başına kesitsel, piyasa = o günün eşit ağırlıklı ortalaması)")
        # 1) IC: her gün özellik ile ileri getiri arasındaki Spearman → günlere göre ortalama
        for ad, fn in ozellikler.items():
            ics = []
            for d in gunler:
                xs = [(fn(r), f) for r, f in gunluk[d] if fn(r) is not None]
                if len(xs) >= 8:
                    ic = spearman([x for x, _ in xs], [y for _, y in xs])
                    if ic is not None:
                        ics.append(ic)
            ortusmesiz = ics[::h]
            res[f'IC_{ad}'] = {'ort': st.mean(ics) if ics else None, 'gun': len(ics),
                               't_ortusmesiz': t_stat(ortusmesiz)}
            if ics:
                print(f"  IC {ad:16s} ort={st.mean(ics):+.3f}  gün={len(ics):3d}  t(örtüşmesiz {len(ortusmesiz)})={t_stat(ortusmesiz):+.2f}")
        # 2) AL tarafı − SAT tarafı farkı (sistemin asıl iddiası)
        farklar = []
        for d in gunler:
            al = [f for r, f in gunluk[d] if (r.get('skor') or 0) >= 2]
            sat = [f for r, f in gunluk[d] if (r.get('skor') or 0) <= -2]
            if al and sat:
                farklar.append(st.mean(al) - st.mean(sat))
        o = farklar[::h]
        res['AL_eksi_SAT'] = {'ort': st.mean(farklar) if farklar else None, 'gun': len(farklar), 't': t_stat(o)}
        if farklar:
            print(f"  AL(skor≥2) − SAT(skor≤−2) ort fark = {st.mean(farklar)*100:+.2f}%  gün={len(farklar)}  t(örtüşmesiz)={t_stat(o):+.2f}")
        # 3) RSI<30 kuralı (sistem +1 puan veriyor)
        x = []
        for d in gunler:
            mkt = st.mean([f for _, f in gunluk[d]])
            x += [f - mkt for r, f in gunluk[d] if (r.get('rsi') or 50) < 30]
        if x:
            print(f"  RSI<30 fazla getiri ort = {st.mean(x)*100:+.2f}%  n={len(x)}  (sistem bunu +1 sayıyor)")
            res['RSI30_fazla'] = st.mean(x)
        rapor['ufuklar'][h] = res
        print()

    # 4) sinyal kararlılığı
    by = collections.defaultdict(dict)
    for (d, sym), r in son.items():
        by[sym][d] = r.get('sinyal')
    cift = deg = 0
    for sym, m in by.items():
        ds = sorted(m)
        for u, v in zip(ds, ds[1:]):
            cift += 1; deg += m[u] != m[v]
    if cift:
        print(f"Kararlılık: ardışık günlerde sinyal değişimi %{deg/cift*100:.0f} ({deg}/{cift})")
        rapor['gunluk_degisim_orani'] = deg / cift
    if a.json:
        json.dump(rapor, open(a.json, 'w'), ensure_ascii=False, indent=1, default=str)


if __name__ == '__main__':
    main()
