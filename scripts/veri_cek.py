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
                    'acilis': s.get('HGDG_AOF'),
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
                        'acilis': round(float(row['Open']), 4) if 'Open' in row else None,
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


def _onceki_is_gunu(tarih_str: str) -> str:
    """PPK karar tarihi: repo uygulama tarihinden 1 iş günü gerisi.

    TCMB yapısal kuralı: PPK kararları Perşembe 14:00'te açıklanır,
    1 hafta repo oranı ertesi iş günü (Cuma) uygulanır. Yani 1 Hafta Repo
    tablosundaki tarih UYGULAMA tarihidir; karar tarihi 1 iş günü öncesidir.
    """
    try:
        d = dt.datetime.strptime(tarih_str, '%d.%m.%Y').date() - dt.timedelta(days=1)
        while d.weekday() >= 5:  # hafta sonunu atla
            d -= dt.timedelta(days=1)
        return d.strftime('%d.%m.%Y')
    except Exception:
        return tarih_str


def tcmb_faizi() -> dict:
    """TCMB 1 Hafta Repo — resmi tablo, SON satır (en güncel karar).

    Tablodaki tarih UYGULAMA tarihidir (ör. 23.01.2026); PPK kararı bir
    önceki iş günü açıklanır (ör. 22.01.2026) → karar_tarihi alanı.
    """
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
                en_guncel = {'tarih': m.group(1), 'faiz': float(m.group(2).replace(',', '.')),
                             'karar_tarihi': _onceki_is_gunu(m.group(1))}
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
            # 2.1 — Zengin açıklamalar (kural bazlı, uydurma yok)
            nedenler = []
            r_rsi = float(son['RSI14'])
            if r_rsi > 70:
                nedenler.append(f"RSI {r_rsi:.0f} → AŞIRI ALIM bölgesi, düzeltme riski")
            elif r_rsi > 55:
                nedenler.append(f"RSI {r_rsi:.0f} → güçlü ama aşırı değil, sağlıklı bölge")
            elif r_rsi < 30:
                nedenler.append(f"RSI {r_rsi:.0f} → AŞIRI SATIM, dip fırsatı olabilir")
            else:
                nedenler.append(f"RSI {r_rsi:.0f} → nötr, yön belirsiz")
            hist = float(son.get('MACD_HIST', 0) or 0)
            if hist > 0:
                nedenler.append(f"MACD sinyal çizgisinin üzerinde (hist {hist:.3f}) → alım momentumu")
            else:
                nedenler.append(f"MACD sinyal çizgisinin altında (hist {hist:.3f}) → satış baskısı")
            r_mfi = float(son['MFI14'])
            if r_mfi > 55:
                nedenler.append(f"MFI {r_mfi:.0f} → net PARA GİRİŞİ (kurumsal alım izi)")
            elif r_mfi < 45:
                nedenler.append(f"MFI {r_mfi:.0f} → PARA ÇIKIŞI, satış baskısı hakim")
            else:
                nedenler.append(f"MFI {r_mfi:.0f} → nötr para akışı")
            nedenler.append(f"PİVOT: {pv['durum']}")
            for anahtar in ('sweep', 'fvg', 'momentum'):
                if anahtar in ict:
                    nedenler.append(f"ICT: {ict[anahtar][1]}")
            if str(son.get('SQUEEZE', '')).upper().startswith('SIKIŞMA'):
                nedenler.append("Bollinger sıkışma → kırılım öncesi birikme")
            # 3.3 — spark: son 30 kapanış (SVG mini grafik için)
            spark = [round(float(x), 2) for x in ind['HGDG_KAPANIS'].iloc[-30:].tolist()]
            # 1 aylık getiri: 22 iş günü önceki kapanışa göre (yeterli bar yoksa None)
            ay_oncesi = None
            if len(ind) >= 23:
                gecen_fiyat = float(ind['HGDG_KAPANIS'].iloc[-23])
                if gecen_fiyat and gecen_fiyat > 0:
                    ay_oncesi = round((float(son['HGDG_KAPANIS']) / gecen_fiyat - 1) * 100, 2)
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
                'ay_oncesi': ay_oncesi,
                'macd_hist': round(hist, 3),
                'spark': spark,
                'nedenler': nedenler[:5],
                'tarih': str(son['HGDG_TARIH'].date()),
            })
        except Exception:
            continue
    sonuclar.sort(key=lambda x: x['skor'], reverse=True)
    # 2.5 — Aşırı alım/satım taraması (mevcut hesaplardan filtreleme)
    tarama = {
        'asiri_satim': [{'sembol': r['sembol'], 'fiyat': r['fiyat'], 'rsi': r['rsi'],
                         'sinyal': r['sinyal'], 'skor': r['skor']} for r in sonuclar if r['rsi'] < 30][:15],
        'asiri_alim': [{'sembol': r['sembol'], 'fiyat': r['fiyat'], 'rsi': r['rsi'],
                        'sinyal': r['sinyal'], 'skor': r['skor']} for r in sonuclar if r['rsi'] > 75][:15],
        'macd_guclu': [{'sembol': r['sembol'], 'fiyat': r['fiyat'], 'rsi': r['rsi'],
                        'sinyal': r['sinyal'], 'skor': r['skor']} for r in sonuclar
                       if r.get('macd_hist', 0) > 0 and r['skor'] >= 2][:15],
    }
    return {
        'al': [r for r in sonuclar if r['sinyal'] in ('AL', 'DİKKAT_AL')][:15],
        'tut': [r for r in sonuclar if r['sinyal'] == 'TUT'][:10],
        'sat': [r for r in sonuclar if r['sinyal'] in ('SAT', 'DİKKAT_SAT')][:10],
        'tarama': tarama,
        'toplam': len(sonuclar),
        'hesap_tarihi': dt.datetime.now().strftime('%d.%m.%Y %H:%M'),
    }


def test_senaryolari(hisse_veri: dict) -> dict:
    """TEST SENARYOLARI — 'geçmişte sinyal olsaydı şu an ne olurdu?' hesabı.

    Gerçek veri + gerçek sinyal geçmişi (uydurma yok):
    - S1 PAZARTESİ AÇILIŞ: cuma kapanışında AL sinyali olan hisse, pazartesi AÇILIŞ fiyatından
      alınıp bugüne kadar tutulursa kar/zarar (tüm pazartesiler, son 6 ay)
    - S2 ERTESI GÜN AÇILIŞ: her AL sinyali gününde, ertesi gün açılışta alınıp tutulursa
    - S3 STOP-LOSS'LU: S2 + girişten sonra -%5 düşerse çık (gerçekçi senaryo)
    - S4 EŞİT AĞIRLIK: tüm sinyaller eşit ağırlıkta portföy (ortalama getiri)
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from indikatorler import tum_indikatorler, sinyal_hesapla
    import pandas as pd

    pazartesi_islemleri = []   # S1
    gunluk_islemler = []       # S2 + S3

    for sembol, rows in hisse_veri.items():
        if len(rows) < 60:
            continue
        df = pd.DataFrame(rows)
        df['HGDG_TARIH'] = pd.to_datetime(df['tarih'])
        df = df.rename(columns={'kapanis': 'HGDG_KAPANIS', 'acilis': 'HGDG_ACILIS',
                                'min': 'HGDG_MIN', 'max': 'HGDG_MAX', 'hacim': 'HGDG_HACIM'})
        df = df.sort_values('HGDG_TARIH').reset_index(drop=True)
        try:
            ind = tum_indikatorler(df)
        except Exception:
            continue
        # Tüm barlarda sinyal üret (son bar hariç — giriş ertesi gün)
        son_fiyat = float(ind['HGDG_KAPANIS'].iloc[-1])
        for i in range(60, len(ind) - 1):
            son = ind.iloc[i]
            s = sinyal_hesapla(son)
            if s['sinyal'] not in ('AL', 'DİKKAT_AL'):
                continue
            giris_gunu = pd.Timestamp(son['HGDG_TARIH']).date()
            # Ertesi günün verileri
            sonraki = ind.iloc[i + 1]
            giris_fiyat = float(sonraki['HGDG_ACILIS']) if pd.notna(sonraki.get('HGDG_ACILIS')) else float(sonraki['HGDG_KAPANIS'])
            if not giris_fiyat or giris_fiyat <= 0:
                continue
            getiri = (son_fiyat / giris_fiyat - 1) * 100
            # S3: stop-loss kontrolü — girişten sonraki barlarda -%5'e düştü mü?
            stop_calismadi = True
            stop_getiri = getiri
            for j in range(i + 1, len(ind)):
                d_ip = (float(ind.iloc[j]['HGDG_MIN']) / giris_fiyat - 1) * 100
                if d_ip <= -5:
                    stop_calismadi = False
                    stop_getiri = -5.0  # %5 stop ile çıkıldı
                    break
            islem = {'sembol': sembol, 'tarih': str(giris_gunu), 'giris': round(giris_fiyat, 2),
                     'bugun': round(son_fiyat, 2), 'getiri_yuzde': round(getiri, 1),
                     'stop_getiri_yuzde': round(stop_getiri, 1), 'stop_calismis': not stop_calismadi,
                     'sinyal_tarih': str(son['HGDG_TARIH'].date())}
            gunluk_islemler.append(islem)
            # S1: cuma sinyali → pazartesi girişi
            if giris_gunu.weekday() == 0:  # pazartesi
                pazartesi_islemleri.append(islem)

    def ozetle(islemler, ad, stop_mu=False):
        if not islemler:
            return {'ad': ad, 'islem': 0, 'ortalama': 0, 'kazanan': 0, 'kaybeden': 0,
                    'en_iyi': None, 'en_kotu': None, 'islemler': []}
        getiriler = [x['stop_getiri_yuzde'] if stop_mu else x['getiri_yuzde'] for x in islemler]
        kazanan = sum(1 for g in getiriler if g > 0)
        return {'ad': ad, 'islem': len(islemler), 'ortalama': round(sum(getiriler) / len(getiriler), 1),
                'kazanan': kazanan, 'kaybeden': len(getiriler) - kazanan,
                'en_iyi': max(islemler, key=lambda x: x['stop_getiri_yuzde'] if stop_mu else x['getiri_yuzde']),
                'en_kotu': min(islemler, key=lambda x: x['stop_getiri_yuzde'] if stop_mu else x['getiri_yuzde']),
                'islemler': sorted(islemler, key=lambda x: x['stop_getiri_yuzde'] if stop_mu else x['getiri_yuzde'], reverse=True)[:15]}

    # 2.3 — Hisse bazlı backtest özeti (hangi hisse kaç kez sinyal verdi, toplam getiri)
    hisse_grup = {}
    for islem in gunluk_islemler:
        hisse_grup.setdefault(islem['sembol'], []).append(islem)
    hisse_ozet = []
    for s, islemler in hisse_grup.items():
        getiriler = [x['getiri_yuzde'] for x in islemler]
        hisse_ozet.append({
            'sembol': s,
            'toplam_getiri': round(sum(getiriler), 1),
            'islem_sayisi': len(islemler),
            'basari_orani': round(sum(1 for g in getiriler if g > 0) / len(getiriler) * 100),
            'max_dusus': round(min(getiriler), 1),
        })
    hisse_ozet.sort(key=lambda x: x['toplam_getiri'], reverse=True)

    return {
        'pazartesi_acilis': ozetle(pazartesi_islemleri, 'Pazartesi açılışında al'),
        'ertesi_gun_acilis': ozetle(gunluk_islemler, 'Sinyal ertesi gün açılışında al'),
        'stop_losslu': ozetle(gunluk_islemler, 'Ertesi gün açılış + %5 stop-loss', stop_mu=True),
        'hisse_bazli': hisse_ozet[:20],
        'aciklama': ('Senaryolar GERÇEK veriyle hesaplanır: sinyal günü kapanışında AL/DİKKAT_AL üreten '
                     'hisse, ertesi gün açılıştan alınır ve bugünkü kapanışla kar/zarar ölçülür. '
                     'Stop-loss senaryosu giriş sonrası -%5 düşüşte çıkış varsayar.'),
    }


def haberler_cek(oncelikli_hisseler=None) -> list:
    """BIST öne çıkan hisselerden gerçek haberler (Yahoo Finance news) + kural bazlı etiket.

    Etiket kuralları (anahtar kelime → duyuru tipi + yön):
    - kar/temettü/sözleşme/ihale/yatırım → pozitif
    - zarar/dava/ceza/soruşturma/istifa → negatif
    Kural dışı haberler nötr etiketlenir — uydurma yorum yok.
    """
    import yfinance as yf
    import warnings
    warnings.filterwarnings('ignore')
    oncelikli = oncelikli_hisseler or ['THYAO', 'AKBNK', 'ASELS', 'GARAN', 'ISCTR', 'KCHOL',
                                       'SAHOL', 'TUPRS', 'EREGL', 'BIMAS']
    pozitif_kw = ['kar', 'kâr', 'temettü', 'sözleşme', 'sozlesme', 'ihale', 'yatırım', 'yatirim',
                  'büyüme', 'buyume', 'rekor', 'anlaşma', 'anlasma', 'artış', 'artis', 'profit',
                  'dividend', 'contract', 'award', 'growth', 'record', 'agreement', 'increase']
    negatif_kw = ['zarar', 'dava', 'ceza', 'soruşturma', 'sorusturma', 'istifa', 'iflas', 'borç', 'borc',
                  'düşüş', 'dusus', 'kayıp', 'kayip', 'loss', 'lawsuit', 'fine', 'investigation',
                  'resign', 'bankruptcy', 'debt', 'decline', 'probe']

    haberler = []
    for sym in oncelikli:
        try:
            t = yf.Ticker(f"{sym}.IS")
            for n in (t.news or [])[:4]:
                c = n.get('content', {})
                baslik = c.get('title', '')
                if not baslik:
                    continue
                yayinci = (c.get('provider') or {}).get('displayName', '')
                tarih = (c.get('pubDate') or '')[:10]
                alt = baslik.lower()
                poz = sum(1 for k in pozitif_kw if k in alt)
                neg = sum(1 for k in negatif_kw if k in alt)
                if poz > neg:
                    yon, etiket = 'pozitif', '🟢 Pozitif'
                elif neg > poz:
                    yon, etiket = 'negatif', '🔴 Negatif'
                else:
                    yon, etiket = 'notr', '⚪ Nötr'
                haberler.append({'sembol': sym, 'baslik': baslik[:160], 'yayinci': yayinci,
                                 'tarih': tarih, 'etiket': etiket, 'yon': yon})
        except Exception:
            continue
    # Tarihe göre sırala (yeniden eskiye), 30 ile sınırla
    haberler.sort(key=lambda x: x['tarih'], reverse=True)
    return haberler[:30]


def fonlar_cek() -> dict:
    """TEFAS fon portföy dağılımları — borsapy Fund.allocation (TEFAS resmi endpoint).

    DİKKAT: TEFAS 'dagilimSiraliGetirT' VARLIK SINIFI bazlı dağılım verir (hisse senedi,
    ters-repo, eurobond...) — hisse BAZLI değil. Hisse bazlı detay TEFAS API key ister.
    Bu yüzden: her fonun varlık sınıfı dağılımı + fonların ortalama hisse senedi ağırlığı gösterilir.
    """
    import borsapy as bp
    import pandas as pd
    # Hisse senedi ağırlıklı fonlar (bilinen A tipi kodlar)
    aday_kodlar = ['TTE', 'TMS', 'TAH', 'TTA', 'TTP', 'AVT', 'TAI']
    sonuc = {'fonlar': [], 'ozet': {}, 'tarih': ''}
    hisse_agirliklari = []
    for kod in aday_kodlar:
        try:
            f = bp.Fund(kod)
            a = f.allocation
            if a is None or (isinstance(a, pd.DataFrame) and a.empty):
                continue
            df = a.dropna(subset=['code'])
            satirlar = []
            hs_agirlik = 0.0
            for _, r in df.iterrows():
                w = float(r.get('weight', 0))
                satirlar.append({'sinif': str(r.get('asset_name', r.get('code', ''))),
                                 'agirlik': round(w, 2)})
                if str(r.get('code', '')).lower() in ('hs', 'yhs'):
                    hs_agirlik += w
            if not satirlar:
                continue
            tarih = str(df.iloc[0].get('Date', ''))[:10]
            # 3.5 — Fon getirileri (TEFAS resmi: 1A/3A/1Y)
            try:
                p = f.performance or {}
                getiri = {'1A': p.get('return_1m'), '3A': p.get('return_3m'),
                          '6A': p.get('return_6m'), '1Y': p.get('return_1y')}
            except Exception:
                getiri = {}
            sonuc['fonlar'].append({'kod': kod, 'tarih': tarih, 'hisse_agirlik': round(hs_agirlik, 1),
                                    'varliklar': satirlar[:8], 'getiri': getiri})
            sonuc['tarih'] = tarih
            hisse_agirliklari.append(hs_agirlik)
        except Exception:
            continue
    if hisse_agirliklari:
        sonuc['ozet'] = {
            'fon_sayisi': len(hisse_agirliklari),
            'ort_hisse_agirlik': round(sum(hisse_agirliklari) / len(hisse_agirliklari), 1),
            'max_hisse_agirlik': round(max(hisse_agirliklari), 1),
        }
    sonuc['not'] = ('TEFAS varlık sınıfı bazlı dağılım verir (hisse senedi, ters-repo, eurobond…). '
                    'Hisse BAZLI dağılım (hangi hisse ne kadar) TEFAS API anahtarı gerektirir.')
    return sonuc


def sektor_dagilimi(bist_list: list) -> dict:
    """Sektör haritası — scripts/sektorler.json (yfinance resmi sınıflandırma).

    Cache dosyası sektor_cek.py ile üretilir; eksik hisse sonraki çalıştırmada
    doldurulur. Sinyal skorlarıyla birleştirme main()'de yapılır.
    """
    try:
        sektor_map = json.loads((Path(__file__).resolve().parent / 'sektorler.json').read_text())
    except Exception:
        return {'map': {}}
    return {'map': sektor_map}


def temel_analiz(bist_list: list, limit: int = 30) -> list:
    """F/K, PD/DD, temettü — yfinance .info (Yahoo resmi). BIST 30 ile sınırlı.

    Skor: F/K<5 (+2), <10 (+1); PD/DD<1 (+2), <1.5 (+1); temettü>%3 (+1).
    """
    import yfinance as yf
    import warnings
    warnings.filterwarnings('ignore')
    sonuclar = []
    for sym in bist_list[:limit]:
        try:
            t = yf.Ticker(f"{sym}.IS")
            info = t.info or {}
            fk = info.get('trailingPE')
            pddd = info.get('priceToBook')
            dy = info.get('dividendYield')
            # Yahoo dividendYield bazen oran (0.03) bazen yüzde (3.0) döner — normalize
            temettu = None
            if dy:
                temettu = round(dy, 1) if dy > 1 else round(dy * 100, 1)
            if fk is None and pddd is None:
                continue
            skor = 0
            if fk is not None:
                if fk < 5:
                    skor += 2
                elif fk < 10:
                    skor += 1
            if pddd is not None:
                if pddd < 1:
                    skor += 2
                elif pddd < 1.5:
                    skor += 1
            if temettu and temettu > 3:
                skor += 1
            sonuclar.append({'sembol': sym, 'fk': round(fk, 1) if fk else None,
                             'pddd': round(pddd, 2) if pddd else None,
                             'temettu': temettu, 'skor': skor})
        except Exception:
            continue
    sonuclar.sort(key=lambda x: x['skor'], reverse=True)
    return sonuclar[:15]


def sinyal_gecmisi_guncelle(sinyaller: dict) -> dict:
    """4 — Sinyal doğruluk takibi: her run'da bugünün sinyallerini günlük dosyaya yaz.

    data/sinyal_gecmisi.json: {'YYYY-MM-DD': {SEMBOL: {sinyal, skor, fiyat}}}
    Aynı gün içinde tekrar yazılırsa üzerine yazılır (dedupe). 45 günden
    eski kayıtlar temizlenir. Dosya repo'ya commit edilir (Actions).
    """
    GECMIS = DATA_DIR / 'sinyal_gecmisi.json'
    try:
        gecmis = json.loads(GECMIS.read_text())
    except Exception:
        gecmis = {}
    bugun = dt.date.today().strftime('%Y-%m-%d')
    bugunun = {}
    for grp in ('al', 'tut', 'sat'):
        for r in sinyaller.get(grp, []):
            bugunun[r['sembol']] = {'sinyal': r['sinyal'], 'skor': r['skor'],
                                    'fiyat': r['fiyat'], 'tarih': bugun}
    if bugunun:
        gecmis[bugun] = bugunun
    eski = (dt.date.today() - dt.timedelta(days=45)).strftime('%Y-%m-%d')
    for k in [k for k in gecmis if k < eski]:
        del gecmis[k]
    GECMIS.write_text(json.dumps(gecmis, ensure_ascii=False), encoding='utf-8')
    log(f"Sinyal geçmişi: {len(gecmis)} gün kayıtlı")
    return gecmis


def sinyal_gecmisi_ozet(gecmis: dict, guncel_fiyatlar: dict) -> dict:
    """4 — Son 7 gün AL/DİKKAT_AL sinyalleri: giriş fiyatı vs bugünkü fiyat → getiri.

    Doğruluk = pozitif getirili sinyal / toplam sinyal (uygulanabilir kayıtlar).
    """
    sonuc = []
    gunler = sorted(gecmis.keys())[-7:]
    for gun in gunler:
        for sembol, info in gecmis[gun].items():
            if info.get('sinyal') not in ('AL', 'DİKKAT_AL'):
                continue
            guncel = guncel_fiyatlar.get(sembol)
            giris = info.get('fiyat')
            getiri = round((guncel / giris - 1) * 100, 1) if guncel and giris else None
            sonuc.append({'tarih': gun, 'sembol': sembol, 'sinyal': info.get('sinyal'),
                          'skor': info.get('skor'), 'giris': giris,
                          'guncel': guncel, 'getiri': getiri})
    poz = sum(1 for x in sonuc if x['getiri'] is not None and x['getiri'] > 0)
    toplam = sum(1 for x in sonuc if x['getiri'] is not None)
    return {
        'kayitlar': sorted(sonuc, key=lambda x: x['tarih'], reverse=True)[:40],
        'basari_orani': round(poz / toplam * 100) if toplam else None,
        'toplam': toplam, 'pozitif': poz,
    }


def gece_analizi(sinyaller: dict, takvim: list) -> dict:
    """5 — Kapanış sonrası özet: yarının kritik seviyeleri + güçlü/zayıf adaylar.

    Tüm veri mevcut hesaplardan türetilir (uydurma yok):
    - En güçlü AL (skor ≥ 3) ve en zayıf SAT (skor ≤ -3) adayları
    - Bollinger sıkışmadakiler (kırılım izlenecek)
    - Aşırı satımlar (RSI < 30)
    - Yarının yüksek önemli makro olayları
    """
    hepsi = sinyaller.get('al', []) + sinyaller.get('tut', []) + sinyaller.get('sat', [])
    guclu = sorted([r for r in hepsi if r.get('skor', 0) >= 3], key=lambda x: -x.get('skor', 0))[:5]
    zayif = sorted([r for r in hepsi if r.get('skor', 0) <= -3], key=lambda x: x.get('skor', 0))[:5]
    squeeze = [r for r in hepsi if 'SIKIŞMA' in str(r.get('squeeze', '')).upper()]
    asiri_satim = [r for r in hepsi if r.get('rsi', 50) < 30]
    yarin = (dt.date.today() + dt.timedelta(days=1)).strftime('%d.%m')
    yarin_olaylar = [o for o in takvim if o.get('tarih') == yarin and o.get('onem') == 'high'][:5]
    return {
        'tarih': dt.datetime.now().strftime('%d.%m.%Y %H:%M'),
        'guclu_al': [{'sembol': r['sembol'], 'skor': r['skor'], 'fiyat': r['fiyat']} for r in guclu],
        'zayif_sat': [{'sembol': r['sembol'], 'skor': r['skor'], 'fiyat': r['fiyat']} for r in zayif],
        'squeeze': [{'sembol': r['sembol'], 'fiyat': r['fiyat'], 'squeeze': r['squeeze']} for r in squeeze[:8]],
        'asiri_satim': [{'sembol': r['sembol'], 'fiyat': r['fiyat'], 'rsi': r['rsi']} for r in asiri_satim[:8]],
        'yarin_yuksek_onem': yarin_olaylar,
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

    # 5. Test senaryoları
    senaryolar = test_senaryolari(hisse_veri) if hisse_veri else {}

    # 5b. Haberler
    haberler = haberler_cek()

    # 5c. Fonlar
    fonlar = fonlar_cek()

    # 5d. Sektör dağılımı (sektorler.json cache + sinyal skorları)
    sektor_cache = sektor_dagilimi(liste)
    sektor_map = sektor_cache.get('map', {})
    sektor_ozet = {}
    for r in sinyaller.get('al', []) + sinyaller.get('tut', []) + sinyaller.get('sat', []):
        sek = sektor_map.get(r['sembol'], 'Bilinmeyen')
        o = sektor_ozet.setdefault(sek, {'hisse_sayisi': 0, 'skor_toplam': 0, 'al': 0, 'sat': 0})
        o['hisse_sayisi'] += 1
        o['skor_toplam'] += r['skor']
        if r['sinyal'] in ('AL', 'DİKKAT_AL'):
            o['al'] += 1
        if r['sinyal'] in ('SAT', 'DİKKAT_SAT'):
            o['sat'] += 1
    sektor_list = []
    for sek, o in sektor_ozet.items():
        sektor_list.append({'sektor': sek, 'hisse_sayisi': o['hisse_sayisi'],
                            'ort_skor': round(o['skor_toplam'] / max(o['hisse_sayisi'], 1), 2),
                            'al': o['al'], 'sat': o['sat']})
    sektor_list.sort(key=lambda x: x['hisse_sayisi'], reverse=True)

    # 5e. Temel analiz (BIST 30 — F/K, PD/DD, temettü)
    temel = temel_analiz(liste)

    # 5f. Sinyal doğruluk geçmişi (madde 4)
    gecmis = sinyal_gecmisi_guncelle(sinyaller)
    guncel_fiyatlar = {r['sembol']: r['fiyat'] for r in
                       sinyaller.get('al', []) + sinyaller.get('tut', []) + sinyaller.get('sat', [])}
    sinyal_gecmisi = sinyal_gecmisi_ozet(gecmis, guncel_fiyatlar)

    # 5g. Gece analizi (madde 5)
    gece = gece_analizi(sinyaller, takvim)

    log(f"Haberler: {len(haberler)} | Fonlar: {len(fonlar.get('fonlar', []))} | "
        f"Sektör: {len(sektor_list)} | Temel analiz: {len(temel)} | "
        f"Doğruluk: {sinyal_gecmisi.get('toplam')} sinyal")

    # 6. JSON yaz
    paket = {
        'uretildi': dt.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        'kaynak': kaynak,
        'endeks': endeks,
        'makro': {'fiyatlar': fiyatlar, 'faiz': faiz, 'tufe': tufe},
        'takvim': takvim,
        'sinyaller': sinyaller,
        'test_senaryolari': senaryolar,
        'haberler': haberler,
        'fonlar': fonlar,
        'sektorler': sektor_list,
        'temel_analiz': temel,
        'sinyal_gecmisi': sinyal_gecmisi,
        'gece_analizi': gece,
    }
    (DATA_DIR / 'piyasa.json').write_text(json.dumps(paket, ensure_ascii=False, indent=1), encoding='utf-8')
    log(f"piyasa.json yazıldı: {os.path.getsize(DATA_DIR / 'piyasa.json')} byte")
    log("=== TAMAM ===")


if __name__ == '__main__':
    main()
