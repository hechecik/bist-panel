#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Altın (ONS/XAU) veri motoru — scripts/altin_cek.py

Üretir → data/altin.json
  fiyat        : ons altın (GC=F) + canlı spot (gold-api) + performans (1g..1y) + gram/TL
  vital        : trend (MA20/50/200), RSI14, ATR14, 52-hafta konum, volatilite
  seviyeler    : destek / direnç (swing pivot + yuvarlak + hareketli ortalama + 52h uç)
  senaryo      : geçmiş → şimdi → gelecek (yukarı/aşağı tetik + hedef + gerekçe)
  kritik_gunler: ABD/küresel yüksek etkili, altın sürücüsü olaylar (doviz.com takvim)
  haberler     : ons altın haber akışı (Google News RSS, TR+EN)

Kaynaklar — hepsi ücretsiz, API ANAHTARI YOK:
  yfinance GC=F              COMEX ons altın (tarihsel OHLC)
  gold-api.com /price/XAU    canlı spot ons
  doviz.com/ekonomik-takvim  ileriye dönük ekonomik takvim
  news.google.com RSS        ons altın haberleri

Anti-halüsinasyon: tüm sayılar gerçek veriden; metinler sayılardan deterministik üretilir.
"""

import json
import os
import re
import sys
import datetime as dt
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

HEADERS = {
    'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/122 Safari/537.36'),
    'Accept-Language': 'tr,en;q=0.8',
}
CIKTI = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'altin.json'))
ONS_GRAM = 31.1034768  # 1 troy ons = 31.1035 gram


def log(m):
    print(f"[altin] {m}", flush=True)


def _get(url, timeout=25, data=None, headers=None):
    h = dict(HEADERS)
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h)
    return urllib.request.urlopen(req, timeout=timeout).read()


# ──────────────────────────────────────────────────────────────
# 1) FİYAT SERİSİ — yfinance GC=F (ons) + gold-api spot
# ──────────────────────────────────────────────────────────────
def ons_seri(periyot='2y'):
    """COMEX ons altın günlük OHLC. yfinance; yoksa global altın uyarısı."""
    try:
        import yfinance as yf
        import warnings
        warnings.filterwarnings('ignore')
    except ImportError:
        log('yfinance yok — ons serisi çekilemedi')
        return None
    df = yf.Ticker('GC=F').history(period=periyot, interval='1d').dropna()
    if df.empty:
        return None
    return df


def spot_fiyat():
    """Canlı spot ons — gold-api.com (anahtar yok)."""
    try:
        j = json.loads(_get('https://api.gold-api.com/price/XAU', timeout=15))
        return float(j['price']), j.get('updatedAt', '')
    except Exception as e:
        log(f'spot hata: {str(e)[:60]}')
        return None, ''


def usdtry():
    try:
        import yfinance as yf
        import warnings
        warnings.filterwarnings('ignore')
        h = yf.Ticker('TRY=X').history(period='5d').dropna()
        return round(float(h['Close'].iloc[-1]), 4) if not h.empty else None
    except Exception:
        return None


def performans(c):
    """1g..1y yüzde değişim (kapanıştan kapanışa)."""
    out = {}
    n_lbl = {'1g': 1, '1h': 5, '2h': 10, '1a': 21, '3a': 63, '6a': 126, '1y': 252}
    for lbl, n in n_lbl.items():
        if len(c) > n and c.iloc[-1 - n]:
            out[lbl] = round((c.iloc[-1] / c.iloc[-1 - n] - 1) * 100, 2)
    return out


# ──────────────────────────────────────────────────────────────
# 2) VİTALLER — trend / RSI / ATR / konum
# ──────────────────────────────────────────────────────────────
def _ema(s, n):
    return s.ewm(alpha=1 / n, adjust=False).mean()


def rsi14(c):
    d = c.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    ru = _ema(up, 14)
    rd = _ema(dn, 14)
    return 100 - 100 / (1 + ru / rd)


def atr14(df):
    h, l, pc = df['High'], df['Low'], df['Close'].shift()
    import pandas as pd
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / 14, adjust=False).mean()


def vitaller(df):
    c = df['Close']
    son = float(c.iloc[-1])
    ma20 = float(c.rolling(20).mean().iloc[-1]) if len(c) >= 20 else None
    ma50 = float(c.rolling(50).mean().iloc[-1]) if len(c) >= 50 else None
    ma200 = float(c.rolling(200).mean().iloc[-1]) if len(c) >= 200 else None
    r = float(rsi14(c).iloc[-1])
    a = float(atr14(df).iloc[-1])
    pencere = df.tail(252)                       # 52-hafta penceresi (intraday uçlar)
    h52, l52 = float(pencere['High'].max()), float(pencere['Low'].min())
    konum = round((son - l52) / (h52 - l52) * 100, 1) if h52 > l52 else 50.0

    # trend sınıflaması (fiyat vs MA'lar)
    ust = lambda ma: ma is not None and son > ma
    if ma50 and ma200 and ust(ma50) and ust(ma200):
        trend, tskor = 'GÜÇLÜ YUKARI', 2
    elif ma50 and ust(ma50):
        trend, tskor = 'TOPARLANIYOR', 1
    elif ma50 and not ust(ma50) and ma200 and not ust(ma200):
        trend, tskor = 'ZAYIF / AŞAĞI', -2
    elif ma50 and not ust(ma50):
        trend, tskor = 'ZAYIF', -1
    else:
        trend, tskor = 'YATAY', 0

    if r >= 70:
        ry = f'{r:.0f} — aşırı alım bölgesi, düzeltme riski'
    elif r >= 55:
        ry = f'{r:.0f} — pozitif momentum'
    elif r >= 45:
        ry = f'{r:.0f} — nötr'
    elif r >= 30:
        ry = f'{r:.0f} — negatif momentum'
    else:
        ry = f'{r:.0f} — aşırı satım bölgesi, tepki potansiyeli'

    return {
        'son': round(son, 2), 'ma20': round(ma20, 2) if ma20 else None,
        'ma50': round(ma50, 2) if ma50 else None, 'ma200': round(ma200, 2) if ma200 else None,
        'trend': trend, 'trend_skor': tskor,
        'rsi': round(r, 1), 'rsi_yorum': ry,
        'atr': round(a, 2), 'atr_yuzde': round(a / son * 100, 2),
        'h52': round(h52, 2), 'l52': round(l52, 2), 'konum_52h': konum,
        'konum_yorum': ('dip bölgesi' if konum < 25 else 'alt bant' if konum < 45
                        else 'orta bant' if konum < 55 else 'üst bant' if konum < 75 else 'zirve bölgesi'),
    }


# ──────────────────────────────────────────────────────────────
# 3) SEVİYELER — destek / direnç
# ──────────────────────────────────────────────────────────────
def _pivotlar(df, k=6):
    hi, lo = [], []
    H, L = df['High'].values, df['Low'].values
    for i in range(k, len(df) - k):
        if H[i] == max(H[i - k:i + k + 1]):
            hi.append(round(float(H[i]), 1))
        if L[i] == min(L[i - k:i + k + 1]):
            lo.append(round(float(L[i]), 1))
    return hi, lo


def yuvarlak(son, yon, adet=6):
    """Sonraki yuvarlak seviyeler (50/100 katları)."""
    adim = 50 if son > 500 else 10
    taban = (int(son // adim) + 1) * adim if yon == 'up' else (int(son // adim)) * adim
    return [taban + i * adim if yon == 'up' else taban - i * adim for i in range(adet)]


def seviyeler(df, v):
    son = v['son']
    hi, lo = _pivotlar(df)
    direnc, destek = [], []

    # direnç adayları: MA'lar + 52h zirve (etiketli) + salınım tepeleri + yuvarlak
    for x, tip in [(v['ma20'], 'MA20'), (v['ma50'], 'MA50'), (v['ma200'], 'MA200'), (v['h52'], '52h zirve')]:
        if x and x > son * 1.001:
            direnc.append((x, tip))
    for x in hi:
        if x > son:
            direnc.append((x, 'salınım tepesi'))
    for x in yuvarlak(son, 'up'):
        direnc.append((x, 'yuvarlak'))
    # destek adayları
    for x, tip in [(v['ma20'], 'MA20'), (v['ma50'], 'MA50'), (v['ma200'], 'MA200'), (v['l52'], '52h dip')]:
        if x and x < son * 0.999:
            destek.append((x, '52h dip' if tip == '52h dip' else tip))
    for x in lo:
        if x < son:
            destek.append((x, 'salınım dibi'))
    for x in yuvarlak(son, 'down'):
        destek.append((x, 'yuvarlak'))

    def paket(liste):
        sec, out = [], []
        for x, tip in sorted(liste, key=lambda t: abs(t[0] - son)):
            if any(abs(x - s) / son < 0.0025 for s in sec):  # %0.25 içindekiler tekilleşir
                continue
            sec.append(x)
            out.append({'seviye': round(x, 1),
                        'mesafe_pct': round((x / son - 1) * 100, 2),
                        'tip': tip})
            if len(out) >= 4:
                break
        return out

    return {'destek': paket(destek), 'direnc': paket(direnc)}


# ──────────────────────────────────────────────────────────────
# 4) SENARYO — geçmiş → şimdi → gelecek
# ──────────────────────────────────────────────────────────────
def senaryo(df, v, perf, sev):
    c = df['Close']
    son = v['son']
    # 52-hafta (252 işlem günü) uçları — vitallerle AYNI pencere (tutarlılık)
    penc = df.tail(252)
    if len(penc) >= 30:
        zirve = float(penc['High'].max()); zirve_t = penc['High'].idxmax().strftime('%m.%Y')
        dip = float(penc['Low'].min());   dip_t = penc['Low'].idxmin().strftime('%m.%Y')
        gectmis = (f"Son 1 yılda ons {dip:,.0f}$ ({dip_t}) ile {zirve:,.0f}$ ({zirve_t}) arasında "
                   f"salındı; şu an {son:,.0f}$ — yıllık zirvenin %{abs((son/zirve-1)*100):.0f} altında, "
                   f"yıllık aralığın %{v['konum_52h']:.0f}'inde.")
    else:
        gectmis = f"Şu an ons {son:,.0f}$."

    # bias skoru: trend + RSI + konum + performans
    skor = v['trend_skor']
    skor += 1 if v['rsi'] >= 55 else (-1 if v['rsi'] < 45 else 0)
    skor += 1 if v['konum_52h'] >= 60 else (-1 if v['konum_52h'] < 40 else 0)
    y1a = perf.get('1a', 0)
    skor += 1 if y1a > 2 else (-1 if y1a < -2 else 0)
    bias = 'BOĞA' if skor >= 2 else 'AYI' if skor <= -2 else 'NÖTR'

    d1 = sev['direnc'][0] if sev['direnc'] else None
    d2 = sev['direnc'][1] if len(sev['direnc']) > 1 else None
    s1 = sev['destek'][0] if sev['destek'] else None
    s2 = sev['destek'][1] if len(sev['destek']) > 1 else None

    yukari = {
        'tetik': d1['seviye'] if d1 else None,
        'hedef': d2['seviye'] if d2 else None,
        'metin': (f"Fiyat {d1['seviye']:,.0f}$ direncini ({(d1['mesafe_pct']):+.1f}%) hacimle kırıp "
                  f"üstünde kapanırsa ilk hedef {d2['seviye']:,.0f}$." if d1 and d2 else
                  'Direnç kırılımı henüz yok.'),
    }
    asagi = {
        'tetik': s1['seviye'] if s1 else None,
        'hedef': s2['seviye'] if s2 else None,
        'metin': (f"{s1['seviye']:,.0f}$ desteği ({(s1['mesafe_pct']):+.1f}%) kaybedilirse "
                  f"sıradaki destek {s2['seviye']:,.0f}$." if s1 and s2 else
                  'Destek kırılımı henüz yok.'),
    }

    durum = (f"Trend {v['trend']}, RSI {v['rsi']:.0f}, yıllık aralığın %{v['konum_52h']:.0f}'inde "
             f"({v['konum_yorum']}). Günlük oynaklık (ATR) {v['atr']:,.0f}$ ≈ %{v['atr_yuzde']:.1f}.")

    return {
        'gectmis': gectmis, 'durum': durum, 'bias': bias, 'bias_skor': skor,
        'yukari': yukari, 'asagi': asagi,
    }


# ──────────────────────────────────────────────────────────────
# 5) KRİTİK GÜNLER — altın sürücüsü olaylar (doviz.com takvim)
# ──────────────────────────────────────────────────────────────
SURUCU = [
    (('fomc', 'fed faiz', 'federal fon'), 'Fed faiz kararı/kararları — altının 1. sürücüsü (düşük faiz = altına destek)'),
    (('çekirdek enflasyon', 'tüfe', 'enflasyon oranı', 'cpi'), 'ABD enflasyonu — Fed faiz patikasını belirler, altını doğrudan iter'),
    (('tarım dışı', 'tarim disi', 'nonfarm', 'nfp', 'i̇stihdam'), 'ABD istihdam — dolar ve Fed beklentisi üzerinden altın'),
    (('pce', 'kişisel tüketim'), "Fed'in tercih ettiği enflasyon ölçüsü — faiz beklentisi"),
    (('powell', 'fed başkanı'), 'Fed Başkanı konuşması — faiz yönlendirmesi'),
    (('faiz kararı', 'faiz oranı', 'interest rate', 'politika faizi'), 'Merkez bankası faiz kararı — altının fırsat maliyeti'),
    (('gsyh', 'gdp', 'büyüme oranı'), 'Büyüme verisi — risk iştahı ve dolar'),
    (('perakende satış', 'retail sales'), 'Tüketici talebi — Fed beklentisi'),
    (('işsizlik', 'i̇şsizlik', 'unemployment'), 'İşgücü görünümü — Fed politikası'),
]


def _neden(olay, ulke=''):
    o = olay.lower()
    abd = ulke in ('ABD', '')
    for anahtarlar, aciklama in SURUCU:
        if any(k in o for k in anahtarlar):
            if abd:
                return aciklama
            if 'enflasyon' in o.lower() or 'faiz' in o.lower():
                return (f'{ulke} enflasyon/faiz verisi — küresel likidite ve dolar endeksi '
                        f'üzerinden altını etkiler')
            return f'{ulke} verisi — küresel risk iştahı / dolar üzerinden altını etkiler'
    return ''


def kritik_gunler(gun=21):
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError:
        return []
    try:
        r = httpx.get('https://www.doviz.com/ekonomik-takvim', timeout=25,
                      follow_redirects=True, headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        log(f'takvim hata: {str(e)[:60]}')
        return []

    aylar = {'ocak': 1, 'şubat': 2, 'mart': 3, 'nisan': 4, 'mayıs': 5, 'haziran': 6,
             'temmuz': 7, 'ağustos': 8, 'eylül': 9, 'ekim': 10, 'kasım': 11, 'aralık': 12}
    gunler = ['Paz', 'Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt']
    bugun = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    son = bugun + dt.timedelta(days=gun)
    kayit = []

    for cid in ['calendar-content-%d' % i for i in range(6)]:
        el = soup.find(id=cid)
        if not el:
            continue
        cur = None
        for child in el.find_all('div', recursive=False):
            cls = child.get('class') or []
            if 'text-bold' in cls:
                m = re.match(r'(\d{1,2})\s+(\S+)\s+(\d{4})', child.get_text().strip())
                if m and aylar.get(m.group(2).lower()):
                    cur = dt.datetime(int(m.group(3)), aylar[m.group(2).lower()], int(m.group(1)))
                continue
            tbl = child.find('table')
            if tbl is None or cur is None or cur < bugun or cur > son:
                continue
            for tr in tbl.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) < 7:
                    continue
                mk = tr.find('span', class_='importance')
                mc = mk.get('class') if mk else []
                imp = next((x for x in mc if x in ('low', 'mid', 'high')), 'low')
                olay = ' '.join(tds[3].get_text(strip=True).split())
                if not olay:
                    continue
                neden = _neden(olay, tds[1].get_text(strip=True))
                # sadece ABD + yüksek/orta önem + altın sürücüsü
                if not neden or imp == 'low' or tds[1].get_text(strip=True) not in ('ABD', 'Euro Bölgesi', 'Çin'):
                    continue
                kayit.append({
                    'tarih': cur.strftime('%d.%m'), 'gun': gunler[cur.weekday()],
                    'saat': tds[0].get_text(strip=True), 'ulke': tds[1].get_text(strip=True),
                    'onem': imp, 'olay': olay, 'neden': neden, 'iso': cur.strftime('%Y-%m-%d'),
                })
    # de-dupe (tarih+saat+olay)
    gor, temiz = set(), []
    for k in kayit:
        key = (k['iso'], k['saat'], k['olay'])
        if key in gor:
            continue
        gor.add(key)
        temiz.append(k)
    temiz.sort(key=lambda x: (x['iso'], x['saat']))
    return temiz[:14]


# ──────────────────────────────────────────────────────────────
# 6) HABERLER — ons altın RSS
# ──────────────────────────────────────────────────────────────
def _rss(url, kaynak, limit=8):
    try:
        raw = _get(url, timeout=15)
        kok = ET.fromstring(raw)
        out = []
        for it in kok.iter('item'):
            b = (it.findtext('title') or '').strip()
            lnk = (it.findtext('link') or '').strip()
            pub = (it.findtext('pubDate') or '').strip()
            if b:
                out.append({'baslik': b[:180], 'kaynak': kaynak, 'link': lnk,
                            'yayin_tarihi': pub})
            if len(out) >= limit:
                break
        return out
    except Exception as e:
        log(f'rss {kaynak} hata: {str(e)[:40]}')
        return []


def haberler():
    kaynaklar = [
        ('https://news.google.com/rss/search?' + urllib.parse.urlencode(
            {'q': 'ons altın fiyat', 'hl': 'tr', 'gl': 'TR', 'ceid': 'TR:tr'}), 'Google News · altın'),
        ('https://news.google.com/rss/search?' + urllib.parse.urlencode(
            {'q': 'gold price forecast Fed', 'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en'}),
         'Google News · gold'),
    ]
    gor, out = set(), []
    for url, ad in kaynaklar:
        for h in _rss(url, ad):
            if h['baslik'][:60] in gor:
                continue
            gor.add(h['baslik'][:60])
            out.append(h)
    return out[:12]


# ──────────────────────────────────────────────────────────────
# ANA
# ──────────────────────────────────────────────────────────────
def main():
    df = ons_seri()
    if df is None or len(df) < 30:
        log('HATA: ons serisi alınamadı (yfinance)')
        sys.exit(1)
    c = df['Close']
    v = vitaller(df)
    perf = performans(c)
    sev = seviyeler(df, v)
    sen = senaryo(df, v, perf, sev)
    spot, spot_t = spot_fiyat()
    fx = usdtry()
    gram = round(v['son'] / ONS_GRAM * fx, 2) if fx else None

    veri = {
        'uretildi': dt.datetime.now().isoformat(timespec='seconds'),
        'kaynak': 'GC=F (COMEX ons) · yfinance + gold-api.com spot + doviz.com takvim',
        'fiyat': {
            'ons': v['son'],
            'spot': round(spot, 2) if spot else None,
            'spot_guncelleme': spot_t,
            'gram_tl': gram,
            'usdtry': fx,
            'performans': perf,
            'son_tarih': df.index[-1].strftime('%Y-%m-%d'),
        },
        'vital': v,
        'seviyeler': sev,
        'senaryo': sen,
        'kritik_gunler': kritik_gunler(21),
        'haberler': haberler(),
    }

    os.makedirs(os.path.dirname(CIKTI), exist_ok=True)
    with open(CIKTI, 'w', encoding='utf-8') as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
    log(f"✅ yazıldı → {CIKTI}")
    log(f"   ons {v['son']}$ · trend {v['trend']} · RSI {v['rsi']} · bias {sen['bias']}")
    log(f"   direnç {[d['seviye'] for d in sev['direnc']]} · destek {[d['seviye'] for d in sev['destek']]}")
    log(f"   kritik gün {len(veri['kritik_gunler'])} · haber {len(veri['haberler'])}")


if __name__ == '__main__':
    main()
