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
FOMC_JSON = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fomc_tarihleri.json'))
# SEP arşivi: her SEP'te FEDTARMD medyanları buraya birikir; revizyon buradan hesaplanır.
SEP_ARSIV = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'sep_arsiv.json'))
ONS_GRAM = 31.1034768  # 1 troy ons = 31.1035 gram
gunler_ad = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']  # weekday(): Pazartesi=0


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
    """Sonraki 100'lük yuvarlak seviyeler (50'lik ara basamaklar kullanılmaz)."""
    adim = 100 if son > 500 else 20
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

    atr = v['atr'] or 0.0
    min_tetik = 0.5 * atr   # tetik fiyattan en az 0.5 ATR uzakta
    min_hedef = 1.0 * atr   # hedef tetikten en az 1 ATR ötede

    # direnç adayları: fiyattan >= 0.5 ATR yukarıda olanlar (yakın olan ilk sırada)
    dy = [d for d in sev['direnc'] if (d['seviye'] - son) >= min_tetik]
    sy = [d for d in sev['destek'] if (son - d['seviye']) >= min_tetik]
    d1 = dy[0] if dy else None
    s1 = sy[0] if sy else None
    # hedef: tetikten >= 1 ATR ötede olan ilk aday
    d2 = next((d for d in dy[1:] if (d['seviye'] - d1['seviye']) >= min_hedef), None) if d1 else None
    s2 = next((d for d in sy[1:] if (s1['seviye'] - d['seviye']) >= min_hedef), None) if s1 else None

    yukari = {
        'tetik': d1['seviye'] if d1 else None,
        'hedef': d2['seviye'] if d2 else None,
        'gecersiz': round(d1['seviye'] - min_tetik, 1) if d1 else None,
        'metin': (f"Fiyat {d1['seviye']:,.0f}$ direncini ({(d1['mesafe_pct']):+.1f}%) kırıp "
                  f"üstünde kapanırsa ilk hedef {d2['seviye']:,.0f}$." if d1 and d2 else
                  'Direnç kırılımı henüz yok.'),
    }
    asagi = {
        'tetik': s1['seviye'] if s1 else None,
        'hedef': s2['seviye'] if s2 else None,
        'gecersiz': round(s1['seviye'] + min_tetik, 1) if s1 else None,
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
    (('üretici fiyat', 'üfe', 'ppi'), 'ABD üretici enflasyonu — TÜFE öncü göstergesi, Fed beklentisi'),
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


def fomc_tarihleri(gun=45):
    """FOMC karar günleri — federalreserve.gov'dan parse, olmazsa scripts/fomc_tarihleri.json.

    Takvim penceresi sınırı UYGULANMAZ: FOMC her zaman listeye girer.
    """
    bugun = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    son = bugun + dt.timedelta(days=gun)
    iso = []

    # 1) canlı parse
    try:
        import httpx
        from bs4 import BeautifulSoup
        r = httpx.get('https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm',
                      timeout=25, follow_redirects=True, headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        aylar = {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                 'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
        # Panel yapısı: div.panel > div.panel-heading(h4 "YYYY FOMC Meetings")
        #               + div.fomc-meeting satırları (month + date hücreleri)
        # NOT: panel metninin tamamını taramak YANLIŞ — basın toplantısı/tutanak
        #      açıklamalarındaki tarihler de eşleşir. Sadece month/date hücreleri okunur.
        for panel in soup.find_all('div', class_='panel'):
            bas = panel.find('h4')
            if not bas:
                continue
            m = re.match(r'\s*(20\d\d)\s+FOMC', bas.get_text(' ', strip=True))
            if not m:
                continue
            yil = int(m.group(1))
            for satir in panel.find_all('div', class_='fomc-meeting'):
                ay_el = satir.find('div', class_='fomc-meeting__month')
                gun_el = satir.find('div', class_='fomc-meeting__date')
                if not ay_el or not gun_el:
                    continue
                ay = ay_el.get_text(' ', strip=True).strip().lower().rstrip('.')
                gtxt = gun_el.get_text(' ', strip=True)
                gm = re.search(r'(\d{1,2})\s*(?:-\s*(\d{1,2}))?', gtxt)   # "*" = projeksiyon
                if ay not in aylar or not gm:
                    continue
                gun_no = int(gm.group(2) or gm.group(1))   # aralıkta SON gün = karar günü
                try:
                    iso.append(dt.date(yil, aylar[ay], gun_no).isoformat())
                except ValueError:
                    pass
        iso = sorted(set(iso))
    except Exception as e:
        log(f'fomc parse hata: {str(e)[:60]}')
        iso = []

    # 2) JSON yedeği
    if not iso:
        try:
            with open(FOMC_JSON, encoding='utf-8') as f:
                j = json.load(f)
            for k, v in j.items():
                if k.startswith('_') or not isinstance(v, list):
                    continue
                iso.extend(x for x in v if isinstance(x, str))
            iso = sorted(set(iso))
        except Exception as e:
            log(f'fomc json hata: {str(e)[:60]}')

    out = []
    for s in iso:
        try:
            d = dt.datetime.strptime(s, '%Y-%m-%d')
        except ValueError:
            continue
        if d < bugun:
            continue          # geçmiş toplantılar atılır
        # Saat sabit YAZILMAZ: 14:00 ET, zoneinfo ile TSİ'ye çevrilir (yaz saati 21:00/22:00).
        try:
            saat_tsi = fomc_tsi(d.strftime('%Y-%m-%d'))['saat_kisa']
        except Exception as e:
            log(f'fomc tsi hata: {str(e)[:50]}')
            saat_tsi = ''
        # Pencere sınırı (son) FOMC'ye UYGULANMAZ — görev: "sınır uygulamadan her zaman ekle"
        out.append({
            'tarih': d.strftime('%d.%m'), 'gun': gunler_ad[d.weekday()], 'saat': saat_tsi,
            'ulke': 'ABD', 'onem': 'high', 'olay': 'FOMC faiz kararı',
            'neden': 'Fed faiz kararı — altının 1. sürücüsü (düşük faiz = altına destek)',
            'iso': d.strftime('%Y-%m-%d'),
        })
    return out


def kritik_gunler(gun=45):
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
    gunler = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']  # weekday(): Pazartesi=0
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
        key = (k['iso'], re.sub(r'\s*\(.*?\)', '', k['olay']).strip().lower())  # saat hariç: ADP 15:15/16:15 tekrarı
        if key in gor:
            continue
        gor.add(key)
        temiz.append(k)
    return temiz


def birlesik_kritik_gunler(gun=45, ust_sinir=14):
    """Takvim olayları + FOMC (sınırsız) → önem (high>mid) sonra tarih sırası, ilk `ust_sinir` kayıt."""
    olaylar = kritik_gunler(gun)
    # FOMC zaten takvimde varsa tekrar ekleme
    mevcut = {(k['iso'], re.sub(r'\s*\(.*?\)', '', k['olay']).strip().lower()) for k in olaylar}
    for f in fomc_tarihleri(gun):
        if (f['iso'], re.sub(r'\s*\(.*?\)', '', f['olay']).strip().lower()) not in mevcut:
            olaylar.append(f)
    onem_sira = {'high': 0, 'mid': 1, 'low': 2}
    olaylar.sort(key=lambda x: (onem_sira.get(x.get('onem', 'low'), 2), x.get('iso', ''), x.get('saat', '')))
    return olaylar[:ust_sinir]


# ──────────────────────────────────────────────────────────────
# 5b) MAKRO SÜRÜCÜLER — FRED + yfinance, anahtarsız (G10)
# ──────────────────────────────────────────────────────────────
FRED_CSV = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id='
# FRED, tarayıcı User-Agent'ı ile bot korumasına takıp bağlantıyı düşürüyor.
# Kendi tanıtıcımız + Accept: text/csv ile anında yanıt veriyor.
FRED_HEADERS = {'User-Agent': 'bist-panel/1.0 (github.com/hechecik/bist-panel)',
                'Accept': 'text/csv,*/*'}
FRED_SERILER = ['DGS2', 'DGS10', 'DFII10', 'T10YIE', 'DFEDTARU', 'DFEDTARL']
SERI_ADLARI = {
    'DGS2': 'ABD 2Y', 'DGS10': 'ABD 10Y nominal', 'DFII10': 'ABD 10Y reel (TIPS)',
    'T10YIE': '10Y başabaş enflasyon', 'DFEDTARU': 'Fed üst bant', 'DFEDTARL': 'Fed alt bant',
}
DOT_YIL_ANAHTAR = {2026: '2026_sonu', 2027: '2027_sonu', 2028: '2028_sonu'}


def fred_seri(seri):
    """FRED CSV → [(date, float)] listesi. Anahtar gerekmez. Hata → []."""
    try:
        raw = _get(FRED_CSV + urllib.parse.quote(seri), timeout=25, headers=FRED_HEADERS).decode('utf-8', 'replace')
    except Exception as e:
        log(f'fred {seri} hata: {str(e)[:50]}')
        return []
    out = []
    for satir in raw.splitlines()[1:]:
        p = satir.split(',')
        if len(p) < 2:
            continue
        try:
            out.append((dt.date.fromisoformat(p[0].strip()), float(p[1])))
        except ValueError:
            continue          # boş / "." / geçersiz gözlem
    return out


def seri_ozet(degerler, altin_seri=None, pencere=60):
    """Son değer + 5/20 günlük değişim + ons ile 60 günlük rolling korelasyon.

    Saf fonksiyon. `degerler`: [(date, float)] eskiden yeniye.
    `altin_seri`: [(date, float)] ons kapanışları; verilirse korelasyon hesaplanır.
    Dönüş: {son, tarih, degisim_5g, degisim_20g, korelasyon_60g, korelasyon_gun}
    """
    if not degerler:
        return {'durum': 'veri yok'}
    son_t, son = degerler[-1]
    out = {'son': round(son, 4), 'tarih': son_t.isoformat(),
           'degisim_5g': None, 'degisim_20g': None,
           'korelasyon_60g': None, 'korelasyon_gun': 0}
    if len(degerler) > 5:
        out['degisim_5g'] = round(son - degerler[-6][1], 4)
    if len(degerler) > 20:
        out['degisim_20g'] = round(son - degerler[-21][1], 4)
    if altin_seri:
        k = rolling_korelasyon(degerler, altin_seri, pencere)
        if k is not None:
            out['korelasyon_60g'] = k[0]
            out['korelasyon_gun'] = k[1]
    return out


def rolling_korelasyon(a, b, pencere=60):
    """İki [(date, float)] serisinin son `pencere` ortak günündeki Pearson korelasyonu.

    Saf fonksiyon (yalnız stdlib). Dönüş: (korelasyon, n) veya None.
    Günler tarih üzerinden hizalanır — FRED tatil günleri ile ölçüm günleri farklı.
    """
    da, db = {}, {}
    for t, v in a:
        da[t] = v
    for t, v in b:
        db[t] = v
    ortak = sorted(set(da) & set(db))
    if len(ortak) < 10:
        return None
    ortak = ortak[-pencere:]
    xa = [da[t] for t in ortak]
    xb = [db[t] for t in ortak]
    n = len(ortak)
    ma, mb = sum(xa) / n, sum(xb) / n
    pay = sum((x - ma) * (y - mb) for x, y in zip(xa, xb))
    pa = sum((x - ma) ** 2 for x in xa) ** 0.5
    pb = sum((y - mb) ** 2 for y in xb) ** 0.5
    if pa == 0 or pb == 0:
        return None
    return round(pay / (pa * pb), 3), n


def sep_arsiv_oku(yol=None):
    """data/sep_arsiv.json → {'kayitlar': [{'sep_tarihi','seyler':{yil:medyan},...}]}. Yoksa boş.

    Saf dosya okuma; dosya yoksa/bozuksa boş yapı döner (uydurma yok).
    """
    yol = yol or SEP_ARSIV
    try:
        with open(yol, encoding='utf-8') as f:
            j = json.load(f)
        k = j.get('kayitlar')
        return {'kayitlar': k if isinstance(k, list) else []}
    except Exception:
        return {'kayitlar': []}


def sep_arsiv_guncelle(medyan, sep_tarihi, yol=None):
    """SEP medyanlarını arşive ekler. Aynı SEP tarihi ikinci kez YAZILMAZ.

    Dönen: güncellenmiş arşiv yapısı. medyan boş/None → arşiv değişmez.
    Saf dosya işlemi (ağ yok).
    """
    yol = yol or SEP_ARSIV
    arsiv = sep_arsiv_oku(yol)
    if not medyan:
        return arsiv
    kayitlar = arsiv['kayitlar']
    mevcut = [k for k in kayitlar if k.get('sep_tarihi') == sep_tarihi]
    if mevcut:
        # Aynı SEP için yalnız eksik yıllar tamamlanır; var olan değer EZİLMEZ.
        s = mevcut[0].setdefault('medyan', {})
        for y, v in medyan.items():
            s.setdefault(str(y), v)
    else:
        kayitlar.append({'sep_tarihi': sep_tarihi,
                         'medyan': {str(y): v for y, v in medyan.items()},
                         'kaynak': 'FRED FEDTARMD'})
        kayitlar.sort(key=lambda k: k.get('sep_tarihi') or '')
    try:
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, 'w', encoding='utf-8') as f:
            json.dump({'kayitlar': kayitlar}, f, ensure_ascii=False, indent=1)
    except Exception as e:
        log(f'sep arsiv yazma hata: {str(e)[:60]}')
    return {'kayitlar': kayitlar}


def onceki_sep_bul(arsiv, bu_sep_tarihi):
    """Arşivden, bu SEP'ten ÖNCEKİ en son SEP kaydının medyanı. Yoksa None."""
    if not arsiv or not arsiv.get('kayitlar') or not bu_sep_tarihi:
        return None
    gecmis = [k for k in arsiv['kayitlar']
              if (k.get('sep_tarihi') or '') < bu_sep_tarihi and k.get('medyan')]
    if not gecmis:
        return None
    return max(gecmis, key=lambda k: k['sep_tarihi']).get('medyan')


def makas_yorumu(makas_bp, esik=25):
    """Dot plot makası deterministik yorumu. Saf fonksiyon."""
    if makas_bp is None:
        return 'veri yok'
    if makas_bp > esik:
        return ('Piyasa Fed’in kendi projeksiyonundan şahin. Güvercin bir SEP '
                'altına pozitif sürpriz olur.')
    if makas_bp < -esik:
        return ('Piyasa Fed’in kendi projeksiyonundan güvercin. Şahin bir SEP '
                'altına negatif sürpriz olur.')
    return 'Uyumlu, sürpriz potansiyeli düşük.'


def sep_revizyon(onceki, yeni, esik=25):
    """SEP medyanı değişimi (bp) → 'şahin revizyon' / 'güvercin revizyon' / 'değişim yok'.

    Saf fonksiyon. Girdiler yüzde (4.1 gibi); değişim baz puana çevrilir.
    """
    if onceki is None or yeni is None:
        return {'degisim_bp': None, 'yorum': 'veri yok'}
    bp = round((yeni - onceki) * 100)
    if bp >= esik:
        yorum = 'şahin revizyon'
    elif bp <= -esik:
        yorum = 'güvercin revizyon'
    else:
        yorum = 'değişim yok'
    return {'degisim_bp': bp, 'yorum': yorum}


def fomc_tsi(iso_tarih, saat_et=14):
    """FOMC karar anı TSİ karşılığı. Saf fonksiyon.

    14:00 ET → New York yaz saati uygulamasına göre 21:00/22:00 TSİ olur;
    sabit yazılmaz, zoneinfo ile hesaplanır. Dönüş: {'tsi':'...','epok':...,'iso_utc':'...'}
    """
    from zoneinfo import ZoneInfo
    d = dt.date.fromisoformat(iso_tarih)
    et = dt.datetime(d.year, d.month, d.day, saat_et, 0, tzinfo=ZoneInfo('America/New_York'))
    tsi = et.astimezone(ZoneInfo('Europe/Istanbul'))
    return {'tsi': tsi.strftime('%d.%m.%Y %H:%M'), 'saat_kisa': tsi.strftime('%H:%M'),
            'iso_utc': et.astimezone(dt.timezone.utc).isoformat(), 'epok': int(et.timestamp())}


def fomc_sayac(iso_tarih, sep=False, simdi=None):
    """Sonraki FOMC sayacı: tarih · TSİ saat · N gün · SEP var/yok. Saf fonksiyon."""
    if not iso_tarih:
        return {'durum': 'veri yok'}
    t = fomc_tsi(iso_tarih)
    simdi = simdi or dt.datetime.now(dt.timezone.utc)
    hedef = dt.datetime.fromisoformat(t['iso_utc'])
    gun = (hedef - simdi).total_seconds() / 86400
    return {'tarih': dt.date.fromisoformat(iso_tarih).strftime('%d.%m.%Y'),
            'saat_tsi': t['saat_kisa'], 'kalan_gun': max(0, int(gun // 1)),
            'kalan_saat': round(max(0.0, gun * 24), 1), 'sep': bool(sep),
            'epok': t['epok'], 'metin': (
                f"Sonraki FOMC: {dt.date.fromisoformat(iso_tarih).strftime('%d.%m.%Y')} "
                f"{t['saat_kisa']} TSİ · {max(0, int(gun // 1))} gün · "
                f"SEP/dot plot {'VAR' if sep else 'YOK'}")}


def _yf_kapanis(ticker, periyot='1y'):
    """yfinance tek sembol günlük kapanış → [(date, float)]. Hata → []."""
    try:
        import yfinance as yf
        h = yf.Ticker(ticker).history(period=periyot)
        if h is None or not len(h):
            return []
        out = []
        for ts, v in h['Close'].items():
            if v != v:            # NaN
                continue
            out.append((ts.date(), float(v)))
        return out
    except Exception as e:
        log(f'yfinance {ticker} hata: {str(e)[:60]}')
        return []


def fed_fonlari_ima(aylar=None):
    """Fed funds vadelilerinden piyasa ima patikası. Saf hesap, ağ yok.

    `aylar`: [{'ay':'YYYY-MM','fiyat':96.0}] → ima faiz = 100 − fiyat.
    Dönüş: {'yillar': {2026: x, 2027: y}, 'kontratlar': [...], 'kaynak': 'vadeli'}
    Her yıl için o yılın SON kontratının ima faizi alınır (yıl sonu patikası).
    """
    if not aylar:
        return None
    yillar = {}
    kontratlar = []
    for k in sorted(aylar, key=lambda x: x['ay']):
        if k.get('fiyat') is None:
            continue
        ima = round(100 - k['fiyat'], 4)
        kontratlar.append({'ay': k['ay'], 'fiyat': round(k['fiyat'], 4), 'ima': ima})
        y, m = k['ay'].split('-')
        yillar[int(y)] = ima          # sıralı → son kontrat kalır
    if not kontratlar:
        return None
    return {'yillar': yillar, 'kontratlar': kontratlar, 'kaynak': 'vadeli'}


def _zq_kontratlari(simdi=None):
    """ZQ (30-gün fed funds) kontrat aylarını çek. yfinance sembolü .CBT uzantılı."""
    simdi = simdi or dt.date.today()
    harfler = ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z']
    # içinde bulunulan aydan itibaren 24 ay
    aylar, y, m = [], simdi.year, simdi.month
    for _ in range(24):
        aylar.append(f'{y}-{m:02d}')
        m += 1
        if m > 12:
            m, y = 1, y + 1
    out = []
    for ay in aylar:
        y, m = ay.split('-')
        sym = f'ZQ{harfler[int(m) - 1]}{y[-2:]}.CBT'
        k = _yf_kapanis(sym, periyot='1mo')
        if not k:
            continue
        out.append({'ay': ay, 'fiyat': round(k[-1][1], 4)})
    return out


def makro_blogu(ons_seri_list=None):
    """altin.json → makro bloğu. FRED+yfinance düşerse 'durum':'veri yok'."""
    out = {'uretildi': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}
    ons = ons_seri_list or []
    seriler = {}
    for s in FRED_SERILER:
        try:
            oz = seri_ozet(fred_seri(s), ons)
            oz['ad'] = SERI_ADLARI.get(s, s)
            seriler[s] = oz
        except Exception as e:
            log(f'makro seri {s} hata: {str(e)[:50]}')
            seriler[s] = {'durum': 'veri yok', 'ad': SERI_ADLARI.get(s, s)}
    out['seriler'] = seriler

    # yfinance: DXY + Brent (ayrı alanlar; WTI ile KARIŞTIRILMAZ)
    piyasa = {}
    for kod, tk, ad in [('dxy', 'DX-Y.NYB', 'DXY · dolar endeksi'),
                        ('brent', 'BZ=F', 'Brent (ICE, BZ=F)')]:
        try:
            oz = seri_ozet(_yf_kapanis(tk), ons)
            oz['ad'] = ad
            oz['sembol'] = tk
            piyasa[kod] = oz
        except Exception as e:
            log(f'makro {kod} hata: {str(e)[:50]}')
            piyasa[kod] = {'durum': 'veri yok', 'ad': ad, 'sembol': tk}
    if piyasa.get('brent', {}).get('son') is not None:
        piyasa['brent']['not'] = 'BZ=F Brent vadeli; WTI ayrı seridir, karıştırılmaz.'
    out['piyasa'] = piyasa

    # Fed faiz bandı (mevcut politika faizi — FRED'den, elle girilmez)
    try:
        ust = fred_seri('DFEDTARU')
        alt = fred_seri('DFEDTARL')
        if ust and alt:
            out['fed_bandi'] = {'ust': round(ust[-1][1], 2), 'alt': round(alt[-1][1], 2),
                                'orta': round((ust[-1][1] + alt[-1][1]) / 2, 4),
                                'tarih': ust[-1][0].isoformat()}
        else:
            out['fed_bandi'] = {'durum': 'veri yok'}
    except Exception:
        out['fed_bandi'] = {'durum': 'veri yok'}

    # Dot plot (FEDTARMD = SEP medyan fed funds, yıl bazında)
    try:
        # FEDTARMD vintage'ı bir SEP toplantısına aittir: son GERÇEKLEŞMİŞ SEP tarihi.
        # Arşive bu tarihle yazılır; böylece aynı SEP tekrar eklenmez ve revizyon
        # bir sonraki SEP'te önceki kayıtla kıyaslanır.
        sep_iso = None
        try:
            sep_iso = _son_sep_tarihi()
        except Exception:
            sep_iso = None
        out['dot_plot'] = dot_plot_blogu(out.get('fed_bandi'), sep_tarihi=sep_iso)
    except Exception as e:
        log(f'dot plot hata: {str(e)[:60]}')
        out['dot_plot'] = {'durum': 'veri yok'}

    # FOMC sayacı
    try:
        out['fomc'] = _fomc_blogu()
    except Exception as e:
        log(f'fomc blogu hata: {str(e)[:60]}')
        out['fomc'] = {'durum': 'veri yok'}

    if all((v.get('durum') == 'veri yok') for v in seriler.values()) and \
            all((v.get('durum') == 'veri yok') for v in piyasa.values()):
        out['durum'] = 'veri yok'
    return out


def dot_plot_blogu(fed_bandi=None, sep_tarihi=None, arsiv_yolu=None):
    """SEP medyanları + piyasa ima patikası + makas_bp + SEP revizyonu.

    Saf hesap + ağ (ZQ) + arşiv dosyası. `sep_tarihi`: bu FEDTARMD vintage'ının
    ait olduğu SEP toplantı tarihi (YYYY-MM-DD); verilmezse bugün kullanılır.
    """
    md = fred_seri('FEDTARMD')
    if not md:
        return {'durum': 'veri yok'}
    # FEDTARMD yıl başı (YYYY-01-01) gözlemleri; aynı yıl için son kayıt geçerli
    medyan = {}
    for t, v in md:
        medyan[t.year] = round(v, 4)
    # Sep revizyonu: bu SEP medyanları arşive yazılır (aynı SEP tekrar yazılmaz),
    # önceki SEP arşivden okunur. Arşiv boşsa revizyon 'veri yok' kalır — UYDURMA yok.
    sep_tarihi = sep_tarihi or dt.date.today().isoformat()
    arsiv = {'kayitlar': []}
    try:
        arsiv = sep_arsiv_guncelle(medyan, sep_tarihi, arsiv_yolu)
        onceki = onceki_sep_bul(arsiv, sep_tarihi)
    except Exception as e:
        log(f'sep arsiv hata: {str(e)[:60]}')
        onceki = None
    simdi_yil = dt.date.today().year
    yillar = sorted(y for y in medyan if y >= simdi_yil)
    if not yillar:
        return {'durum': 'veri yok'}
    # Karşılaştırma yılı: bir sonraki yılın SEP medyanı (cari yılı geçen ilk yıl).
    # Cari yıl medyanı zaten bugünün politikasını yansıtır; piyasa patikasının
    # 1 yıl ilerisiyle kıyaslanması gerekir.
    hedef_yil = next((y for y in yillar if y > simdi_yil), yillar[-1])

    # Revizyon: hedef yıl için önceki SEP medyanı varsa bp farkı hesaplanır.
    onceki_deger = None
    if onceki:
        onceki_deger = onceki.get(str(hedef_yil), onceki.get(hedef_yil))
    sonuc = {'medyan': {str(y): medyan[y] for y in yillar},
             'onceki_sep_medyan': onceki,
             'onceki_sep_tarihi': (max((k.get('sep_tarihi') or '' for k in arsiv['kayitlar']
                                        if (k.get('sep_tarihi') or '') < sep_tarihi
                                        and k.get('medyan')), default=None)
                                   if onceki else None),
             'revizyon': sep_revizyon(onceki_deger, medyan.get(hedef_yil)),
             'revizyon_yil': hedef_yil,
             'sep_tarihi': sep_tarihi,
             'hedef_yil': hedef_yil,
             'kaynak': 'FRED FEDTARMD (SEP medyan fed funds projeksiyonu)'}

    # Piyasa ima patikası
    ima = None
    try:
        ima = fed_fonlari_ima(_zq_kontratlari())
    except Exception as e:
        log(f'zq hata: {str(e)[:50]}')
    if not ima:
        # Proxy: 2Y getirisi − mevcut faiz (etiketlenir, uydurma değil)
        try:
            dgs2 = fred_seri('DGS2')
            if dgs2 and fed_bandi and fed_bandi.get('orta') is not None:
                ima = {'kaynak': 'proxy', 'not': 'ZQ kontratı alınamadı → 2Y − mevcut faiz (proxy)',
                       'yillar': {sonuc['hedef_yil']: round(dgs2[-1][1], 4)},
                       'proxy_fark': round(dgs2[-1][1] - fed_bandi['orta'], 4)}
        except Exception:
            ima = None
    sonuc['piyasa_ima'] = ima

    # makas_bp = (piyasa − dot) × 100 — dot ile piyasa AYNI yıl için kıyaslanır
    makas, makas_yil = None, None
    if ima and ima.get('yillar'):
        if ima.get('kaynak') == 'proxy':
            # proxy patika SEVİYESİ değil FARK verir (2Y − mevcut faiz), o yüzden
            # cari yıl SEP medyanı değil, proxy farkı bp olarak raporlanır.
            if medyan.get(simdi_yil) is not None:
                makas = round(ima.get('proxy_fark', 0) * 100)
                makas_yil = simdi_yil
        else:
            # Piyasanın hedef yıl sonu ima faizi varsa onu kullan; yoksa en yakın
            # (hedeften küçük) yılın son kontratına düş ve etiketle.
            uygun = [y for y in ima['yillar'] if y in medyan]
            if uygun:
                y = hedef_yil if hedef_yil in uygun else min(uygun, key=lambda x: abs(x - hedef_yil))
                makas = round((ima['yillar'][y] - medyan[y]) * 100)
                makas_yil = y
    sonuc['makas_bp'] = makas
    sonuc['makas_yil'] = makas_yil
    sonuc['yorum'] = makas_yorumu(makas)
    return sonuc


def _fomc_iso_haritasi():
    """FOMC tarihleri → {iso: sep(bool)}. Önce canlı parse, olmazsa yedek JSON."""
    iso_map = {}   # iso -> sep(bool)
    # 1) canlı parse (SEP yıldızı "*" ile işaretli)
    try:
        import httpx
        from bs4 import BeautifulSoup
        r = httpx.get('https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm',
                      timeout=25, follow_redirects=True, headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        aylar = {'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                 'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12}
        for panel in soup.find_all('div', class_='panel'):
            bas = panel.find('h4')
            if not bas:
                continue
            m = re.match(r'\s*(20\d\d)\s+FOMC', bas.get_text(' ', strip=True))
            if not m:
                continue
            yil = int(m.group(1))
            for satir in panel.find_all('div', class_='fomc-meeting'):
                ay_el = satir.find('div', class_='fomc-meeting__month')
                gun_el = satir.find('div', class_='fomc-meeting__date')
                if not ay_el or not gun_el:
                    continue
                ay = ay_el.get_text(' ', strip=True).strip().lower().rstrip('.')
                gtxt = gun_el.get_text(' ', strip=True)
                gm = re.search(r'(\d{1,2})\s*(?:-\s*(\d{1,2}))?', gtxt)
                if ay not in aylar or not gm:
                    continue
                gun_no = int(gm.group(2) or gm.group(1))
                try:
                    iso_map[dt.date(yil, aylar[ay], gun_no).isoformat()] = '*' in gtxt
                except ValueError:
                    pass
    except Exception as e:
        log(f'fomc sep parse hata: {str(e)[:50]}')

    # 2) yedek JSON (SEP bayrağı JSON'da yoksa sep_tarihleri listesinden)
    if not iso_map:
        try:
            with open(FOMC_JSON, encoding='utf-8') as f:
                j = json.load(f)
            seps = set(j.get('_sep', []))
            for k, v in j.items():
                if k.startswith('_') or not isinstance(v, list):
                    continue
                for x in v:
                    if isinstance(x, str):
                        iso_map[x] = x in seps
        except Exception as e:
            log(f'fomc json hata: {str(e)[:60]}')
    return iso_map


def _son_sep_tarihi(bugun=None, iso_map=None):
    """Son GERÇEKLEŞMİŞ SEP toplantı tarihi (YYYY-MM-DD). Bulunamazsa None.

    FEDTARMD serisi her zaman en son yayımlanan SEP'in medyanlarını tutar;
    arşive bu tarihle yazılır ki aynı SEP her çalıştırmada tekrar eklenmesin.
    """
    iso_map = iso_map if iso_map is not None else _fomc_iso_haritasi()
    bugun = bugun or dt.date.today()
    gecmis_sep = [x for x, sep in iso_map.items() if sep and dt.date.fromisoformat(x) <= bugun]
    return max(gecmis_sep) if gecmis_sep else None


def _fomc_blogu():
    """fomc_tarihleri.json + canlı parse → sonraki toplantı, TSİ saat, SEP bayrağı."""
    iso_map = _fomc_iso_haritasi()
    bugun = dt.date.today()
    gelecek = sorted(x for x in iso_map if dt.date.fromisoformat(x) >= bugun)
    if not gelecek:
        return {'durum': 'veri yok'}
    nxt = gelecek[0]
    s = fomc_sayac(nxt, iso_map.get(nxt, False))
    s['sonraki_liste'] = [{'tarih': x, 'sep': iso_map[x],
                           'tsi': fomc_tsi(x)['saat_kisa']} for x in gelecek[:6]]
    s['kaynak'] = 'federalreserve.gov FOMC takvimi'
    return s


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
def manset(spot, fx, vadeli_ons):
    """Manşet ons/gram hesabı (saf fonksiyon, ağa çıkmaz).

    spot varsa SPOT bazlı, yoksa GC=F (vadeli) bazlı manşet döner.
    gram = ons / 31.1034768 * usdtry
    """
    if spot and fx:
        ons = round(spot, 2)
        tip = 'spot'
    else:
        ons = round(vadeli_ons, 2) if vadeli_ons else None
        tip = 'vadeli'
    gram = round(ons / ONS_GRAM * fx, 2) if (ons and fx) else None
    return {'ons': ons, 'kaynak_tipi': tip, 'gram_tl': gram}


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

    # Manşet fiyat SPOT'tan; GC=F (vadeli) yalnızca tarihsel seri için
    mh = manset(spot, fx, v['son'])
    ons_manşet, kaynak_tipi, gram = mh['ons'], mh['kaynak_tipi'], mh['gram_tl']

    # G10: makro sürücüler — kendi try/except'i içinde, düşerse altın blokları etkilenmez
    try:
        makro = makro_blogu([(t.date(), float(v)) for t, v in c.items()])
    except Exception as e:
        log(f'makro blok HATA: {str(e)[:80]}')
        makro = {'durum': 'veri yok'}

    veri = {
        'uretildi': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'kaynak': 'gold-api.com spot (manşet) · GC=F COMEX vadeli (tarihsel seri) · doviz.com takvim',
        'fiyat': {
            'ons': ons_manşet,
            'kaynak_tipi': kaynak_tipi,
            'vadeli_ons': v['son'],
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
        'kritik_gunler': birlesik_kritik_gunler(45),
        'haberler': haberler(),
        'makro': makro,
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
