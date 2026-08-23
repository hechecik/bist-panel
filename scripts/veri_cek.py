#!/usr/bin/env python3
"""BIST PANEL — veri çekme scripti (GitHub Actions'ta çalışır).

Tüm veriler GERÇEK kaynaklardan çekilir — anti-hallüsinasyon:
- Hisse OHLCV: İş Yatırım HisseTekil (TR API) → çalışmazsa yfinance yedeği
- BIST 100 endeks: yfinance ^XU100.IS
- Altın/döviz/emtia: borsapy (doviz.com alt yapısı) + yfinance çapraz
- Ekonomik takvim: doviz.com parse
- TCMB politika faizi: TCMB resmi tablo (borsapy bug'li — kendi parse'ımız)
- TÜFE: borsapy (TCMB resmi)

Çıktı: data/*.json — site bu dosyaları okur.
Hiçbir API key, kişisel bilgi, IP adresi bu script'te yok. OPSEC temiz.
"""
import json, os, sys, re
import datetime as dt
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'}

# BIST 100 bileşenleri (KAP resmi listesinden sabitlenmiş — repo içinde bist100.txt)
BIST100_FILE = Path(__file__).resolve().parent.parent / "bist100.txt"


def log(msg):
    print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def bist100_listesi() -> list:
    """BIST 100 hisse listesi — repo içindeki sabit dosyadan."""
    if BIST100_FILE.exists():
        return [l.strip().upper() for l in BIST100_FILE.read_text().splitlines() if l.strip()]
    # Fallback: bilinen ana hisseler
    return ['THYAO','AKBNK','ASELS','GARAN','ISCTR','KCHOL','SAHOL','TUPRS','EREGL','BIMAS',
            'FROTO','PETKM','SISE','TCELL','TAVHL','YKBNK','HEKTS','SASA','EKGYO','TOASO',
            'KRDMD','OTKAR','AEFES','BRSAN','CCOLA','ENKAI','KOZAL','PGSUS','SOKM','TKFEN',
            'AGHOL','AKSA','ALARK','ARCLK','BAGFS','BRISA','DOAS','GUBRF','ISDMR','KCHOL',
            'MAVI','MGROS','ODINE','OYAKC','SMRTG','SODA','TMSN','TTKOM','VESTL','ZOREN']


def cek_isyatirim(bist_list: list) -> list | None:
    """İş Yatırım HisseTekil — tek istekte tüm hisseler. Yurt dışı IP engeli olabilir."""
    try:
        import requests
        url = "https://public.finance.isyatirim.com.tr/FintechServices.svc/HisseTekil"
        payload = {"HisseTekil": {"HacimAdedi": 10000000, "Kur": "TL",
                                   "VeriTipi": "1", "VeriTipi2": "2", "Yil": "2"}}
        r = requests.post(url, json=payload, timeout=30,
                          headers={**HEADERS, 'Content-Type': 'application/json'})
        if r.status_code != 200:
            log(f"İş Yatırım: HTTP {r.status_code} — yfinance'a geçilecek")
            return None
        data = r.json()
        satirlar = data.get('HisseTekil', {}).get('HisseTekil', [])
        if not satirlar:
            log("İş Yatırım: boş yanıt — yfinance'a geçilecek")
            return None
        # {sembol: [tarih, kapanis, min, max, hacim, PD...]}
        semboller = set(bist_list)
        hisse_veri = {}
        for s in satirlar:
            kod = str(s.get('HisseKodu', '')).upper()
            if kod not in semboller:
                continue
            h = hisse_veri.setdefault(kod, [])
            try:
                h.append({
                    'tarih': s['Tarih'][:10],
                    'kapanis': s.get('HGDG_Kapanis'),
                    'min': s.get('HGDG_Min'),
                    'max': s.get('HGDG_Max'),
                    'hacim': s.get('HGDG_Hacim'),
                })
            except Exception:
                continue
        log(f"İş Yatırım OK: {len(hisse_veri)} hisse")
        return hisse_veri
    except Exception as e:
        log(f"İş Yatırım hata: {str(e)[:60]} — yfinance'a geçilecek")
        return None


def cek_yfinance(bist_list: list) -> dict:
    """yfinance — çoklu sembol tek istekte (Actions ABD IP'den garantili çalışır)."""
    import yfinance as yf
    import pandas as pd
    tickers = [f"{s}.IS" for s in bist_list]
    veri = {}
    try:
        df = yf.download(tickers, period="6mo", interval="1d",
                         group_by="ticker", auto_adjust=False, progress=False,
                         threads=True)
        for s, t in zip(bist_list, tickers):
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    sub = df[t]
                else:
                    sub = df
                if sub.empty or 'Close' not in sub:
                    continue
                rows = []
                for idx, row in sub.dropna(subset=['Close']).iterrows():
                    rows.append({
                        'tarih': str(idx.date()),
                        'kapanis': round(float(row['Close']), 4),
                        'min': round(float(row['Low']), 4) if 'Low' in row else None,
                        'max': round(float(row['High']), 4) if 'High' in row else None,
                        'hacim': int(row['Volume']) if 'Volume' in row else None,
                    })
                if rows:
                    veri[s] = rows
            except Exception:
                continue
    except Exception as e:
        log(f"yfinance toplu hata: {str(e)[:80]}")
    log(f"yfinance OK: {len(veri)} hisse")
    return veri


def endeks_verisi() -> dict | None:
    """BIST 100 endeks — yfinance XU100.IS (^XU100.IS sembolü Yahoo'da yok)."""
    try:
        import yfinance as yf
        import pandas as pd
        df = yf.download("XU100.IS", period="6mo", interval="1d", progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df = df.xs("XU100.IS", axis=1, level="Ticker")
        son = df.iloc[-1]
        onceki = df.iloc[-2] if len(df) > 1 else son
        return {
            'deger': round(float(son['Close']), 2),
            'degisim_yuzde': round((float(son['Close']) / float(onceki['Close']) - 1) * 100, 2),
            'tarih': str(df.index[-1].date()),
        }
    except Exception as e:
        log(f"Endeks hata: {str(e)[:60]}")
        return None


def makro_fiyatlar() -> dict:
    """Altın/döviz/emtia — borsapy FX (doviz.com) + ons için yfinance."""
    fiyatlar = {}
    try:
        import borsapy as bp
        semboller = {'gram-altin': ('GRAM ALTIN', 'TL/gram'), 'USD': ('DOLAR/TL', 'TL'),
                     'EUR': ('EURO/TL', 'TL'), 'BRENT': ('BRENT', 'USD/varil'),
                     'XAG-USD': ('GÜMÜŞ', 'USD/ons')}
        for sym, (ad, birim) in semboller.items():
            try:
                c = bp.FX(sym).current
                son = c.get('last')
                acilis = c.get('open')
                fiyatlar[sym] = {'ad': ad, 'birim': birim, 'fiyat': round(float(son), 2) if son else None,
                                 'degisim': round((float(son) / float(acilis) - 1) * 100, 2) if son and acilis else None}
            except Exception:
                continue
    except Exception as e:
        log(f"borsapy FX hata: {str(e)[:50]}")
    # ONS altın — yfinance GC=F (borsapy yarım değer veriyor)
    try:
        import yfinance as yf
        import warnings
        warnings.filterwarnings('ignore')
        g = yf.Ticker('GC=F').history(period='2d')
        son = float(g['Close'].iloc[-1])
        onceki = float(g['Close'].iloc[-2]) if len(g) > 1 else son
        fiyatlar['ons-altin'] = {'ad': 'ONS ALTIN', 'birim': 'USD/ons', 'fiyat': round(son, 2),
                                 'degisim': round((son / onceki - 1) * 100, 2) if onceki else None}
    except Exception as e:
        log(f"ons altın hata: {str(e)[:50]}")
    return fiyatlar


def takvim_cek(gun_sayisi: int = 7) -> list:
    """Ekonomik takvim — doviz.com parse (TR + ABD önemli olaylar)."""
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError:
        return []
    try:
        r = httpx.get('https://www.doviz.com/ekonomik-takvim', timeout=25, follow_redirects=True, headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
    except Exception:
        return []
    aylar = {'ocak':1,'şubat':2,'mart':3,'nisan':4,'mayıs':5,'haziran':6,
             'temmuz':7,'ağustos':8,'eylül':9,'ekim':10,'kasım':11,'aralık':12}
    olaylar = []
    bugun = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    son = bugun + dt.timedelta(days=gun_sayisi)
    for cid in ['calendar-content-0','calendar-content-1','calendar-content-2','calendar-content-3']:
        el = soup.find(id=cid)
        if not el:
            continue
        cur = None
        for child in el.find_all(['div'], recursive=False):
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
                marker = tr.find('span', class_='importance')
                mc = marker.get('class') if marker else []
                imp = next((c for c in mc if c in ('low','mid','high')), 'low')
                olay = ' '.join(tds[3].get_text(strip=True).split())
                if not olay:
                    continue
                olaylar.append({'tarih': cur.strftime('%d.%m'), 'saat': tds[0].get_text(strip=True),
                                'ulke': tds[1].get_text(strip=True), 'onem': imp, 'olay': olay})
    # de-dupe + TR/ABD önemli filtre
    gorulen = set()
    temiz = []
    for o in olaylar:
        k = (o['tarih'], o['saat'], o['olay'])
        if k in gorulen or o['ulke'] not in ('ABD', 'Türkiye'):
            continue
        gorulen.add(k)
        temiz.append(o)
    return temiz[:25]


def tcmb_faizi() -> dict:
    """TCMB 1 Hafta Repo — resmi tablo, SON satır (en güncel karar)."""
    try:
        import httpx
        from bs4 import BeautifulSoup
        url = ("https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Temel+Faaliyetler/"
               "Para+Politikasi/Merkez+Bankasi+Faiz+Oranlari/1+Hafta+Repo")
        r = httpx.get(url, timeout=25, follow_redirects=True, headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        en_guncel = None
        for tr in soup.find_all('tr'):
            satir = ' '.join(td.get_text(strip=True) for td in tr.find_all('td'))
            m = re.match(r'(\d{1,2}\.\d{1,2}\.\d{4})\D+([\d,\.]+)\s*$', satir)
            if m:
                en_guncel = {'tarih': m.group(1), 'faiz': float(m.group(2).replace(',', '.'))}
        return en_guncel or {}
    except Exception as e:
        log(f"TCMB hata: {str(e)[:50]}")
        return {}


def tufe_verisi() -> dict:
    """TÜFE — borsapy (TCMB resmi)."""
    try:
        import borsapy as bp
        enf = bp.Inflation().latest('tufe')
        return {'tarih': enf.get('year_month'), 'yillik': round(float(enf.get('yearly_inflation')), 2)}
    except Exception:
        return {}


def sinyalleri_hesapla(hisse_veri: dict) -> dict:
    """OHLCV verisinden indikatör + sinyal hesapla (indikatorler.py mantığı)."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from indikatorler import tum_indikatorler, sinyal_hesapla, pivot_seviyeler, seviye_durumu, ict_sinyalleri
    import pandas as pd

    sonuclar = []
    for sembol, rows in hisse_veri.items():
        if len(rows) < 60:
            continue
        df = pd.DataFrame(rows)
        df['HGDG_TARIH'] = pd.to_datetime(df['tarih'])
        df = df.rename(columns={'kapanis': 'HGDG_KAPANIS', 'min': 'HGDG_MIN', 'max': 'HGDG_MAX', 'hacim': 'HGDG_HACIM'})
        df = df.sort_values('HGDG_TARIH').reset_index(drop=True)
        try:
            ind = tum_indikatorler(df)
            son = ind.iloc[-1]
            s = sinyal_hesapla(son)
            pv = pivot_seviyeler(ind['HGDG_MAX'], ind['HGDG_MIN'], ind['HGDG_KAPANIS'])
            pv['durum'] = seviye_durumu(son['HGDG_KAPANIS'], pv)
            ict = ict_sinyalleri(ind)
            nedenler = [f"RSI {son['RSI14']:.0f} trend {s['trend']}",
                        f"MFI {son['MFI14']:.0f} ({s['para_akis']})",
                        f"PİVOT: {pv['durum']}"]
            for anahtar in ('sweep', 'fvg', 'momentum'):
                if anahtar in ict:
                    nedenler.append(f"ICT: {ict[anahtar][1]}")
            sonuclar.append({
                'sembol': sembol,
                'fiyat': round(float(son['HGDG_KAPANIS']), 2),
                'skor': s['skor'],
                'sinyal': s['sinyal'],
                'trend': s['trend'],
                'rsi': round(float(son['RSI14']), 1),
                'mfi': round(float(son['MFI14']), 1),
                'para': s['para_akis'],
                's1': pv['s1'], 'r1': pv['r1'],
                'stop': s['stop_loss'], 'hedef': s['hedef'],
                'squeeze': son.get('SQUEEZE', 'NORMAL'),
                'nedenler': nedenler[:5],
                'tarih': str(son['HGDG_TARIH'].date()),
            })
        except Exception:
            continue
    sonuclar.sort(key=lambda x: x['skor'], reverse=True)
    return {
        'al': [r for r in sonuclar if r['sinyal'] in ('AL', 'DİKKAT_AL')][:15],
        'tut': [r for r in sonuclar if r['sinyal'] == 'TUT'][:10],
        'sat': [r for r in sonuclar if r['sinyal'] in ('SAT', 'DİKKAT_SAT')][:10],
        'toplam': len(sonuclar),
        'hesap_tarihi': dt.datetime.now().strftime('%d.%m.%Y %H:%M'),
    }


def main():
    log("=== BIST PANEL veri çekme başladı ===")
    liste = bist100_listesi()
    log(f"BIST 100 listesi: {len(liste)} hisse")

    # 1. Hisse verisi: İş Yatırım → yfinance yedeği
    hisse_veri = cek_isyatirim(liste)
    kaynak = "isyatirim"
    if not hisse_veri:
        hisse_veri = cek_yfinance(liste)
        kaynak = "yfinance"
    if not hisse_veri:
        log("KRİTİK: hisse verisi alınamadı")
        hisse_veri = {}

    # 2. Endeks
    endeks = endeks_verisi()

    # 3. Makro
    fiyatlar = makro_fiyatlar()
    takvim = takvim_cek()
    faiz = tcmb_faizi()
    tufe = tufe_verisi()

    # 4. Sinyaller
    sinyaller = sinyalleri_hesapla(hisse_veri) if hisse_veri else {'al': [], 'tut': [], 'sat': [], 'toplam': 0, 'hesap_tarihi': ''}

    # 5. JSON yaz
    paket = {
        'uretildi': dt.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        'kaynak': kaynak,
        'endeks': endeks,
        'makro': {'fiyatlar': fiyatlar, 'faiz': faiz, 'tufe': tufe},
        'takvim': takvim,
        'sinyaller': sinyaller,
    }
    (DATA_DIR / 'piyasa.json').write_text(json.dumps(paket, ensure_ascii=False, indent=1), encoding='utf-8')
    log(f"piyasa.json yazıldı: {os.path.getsize(DATA_DIR / 'piyasa.json')} byte")
    log("=== TAMAM ===")


if __name__ == '__main__':
    main()
