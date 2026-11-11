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
import urllib.request
from pathlib import Path


def utc_now_iso() -> str:
    """Tüm zaman damgaları timezone-aware UTC (UI TR saatine çevirir)."""
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')

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
        # '#' ile başlayan satırlar yorumdur (ör. "# güncelleme: 2026-11-11")
        return [l.strip().upper() for l in BIST100_FILE.read_text().splitlines()
                if l.strip() and not l.strip().startswith('#')]
    # Fallback: bilinen ana hisseler
    return ['THYAO','AKBNK','ASELS','GARAN','ISCTR','KCHOL','SAHOL','TUPRS','EREGL','BIMAS',
            'FROTO','PETKM','SISE','TCELL','TAVHL','YKBNK','HEKTS','SASA','EKGYO','TOASO',
            'KRDMD','OTKAR','AEFES','BRSAN','CCOLA','ENKAI','KOZAL','PGSUS','SOKM','TKFEN',
            'AGHOL','AKSA','ALARK','ARCLK','BAGFS','BRISA','DOAS','GUBRF','ISDMR',
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
            log(f"İş Yatırım: HTTP {r.status_code} — borsapy deneniyor")
            return None
        data = r.json()
        satirlar = data.get('HisseTekil', {}).get('HisseTekil', [])
        if not satirlar:
            log("İş Yatırım: boş yanıt — borsapy deneniyor")
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


def cek_borsapy(bist_list: list) -> dict:
    """2. KADEME — borsapy TradingView provider (İş Yatırım'dan BAĞIMSIZ).

    borsapy Ticker.history() kendi calendar.py çakışması yüzünden bug'li —
    provider doğrudan kullanılır. TradingView global olduğu için Actions
    ABD IP'sinde de çalışır. Tek istek/hisse (~1 sn) — 100 hisse ~2 dk.
    """
    try:
        from borsapy._providers.tradingview import get_tradingview_provider
        import pandas as pd
    except Exception:
        return {}
    veri = {}
    try:
        p = get_tradingview_provider()
        for sym in bist_list:
            try:
                df = p.get_history(sym, interval='1d', period='1y')  # SMA200 için ≥200 bar şart
                if df is None or len(df) < 60:
                    continue
                rows = []
                for idx, row in df.iterrows():
                    k = float(row['Close'])
                    if k != k or k <= 0:  # NaN/pozitif kontrol
                        continue
                    rows.append({
                        'tarih': str(pd.Timestamp(idx).date()),
                        'kapanis': round(k, 4),
                        'acilis': round(float(row['Open']), 4),
                        'min': round(float(row['Low']), 4),
                        'max': round(float(row['High']), 4),
                        'hacim': int(row['Volume']) if row['Volume'] == row['Volume'] else None,
                    })
                if rows:
                    veri[sym] = rows
            except Exception:
                continue
    except Exception as e:
        log(f"borsapy (TradingView) hata: {str(e)[:60]}")
    log(f"borsapy (TradingView) OK: {len(veri)} hisse")
    return veri


BOLUNME_ESIK = -0.30   # bundan düşük günlük kapanış değişimi fiziksel olarak imkânsız (BIST marjı ±%10)


def _guvenli(v):
    """None/NaN güvenli float dönüşümü — geçersizse None."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def bolunme_tespit(rows: list, esik: float = BOLUNME_ESIK) -> list:
    """Düzeltilmemiş bedelsiz bölünme (split) sıçramalarını tespit eder — SAF fonksiyon.

    Mantık: BIST'te günlük fiyat marjı ±%10. Bir günün kapanışı önceki günün
    kapanışına göre %30'dan fazla düşmüşse bu gerçek bir fiyat hareketi olamaz;
    seri bölünmeye göre düzeltilmemiştir.

    Kural (G02):
    - Kapanış değişimi `esik`in (-0.30) altında olmalı → −%10..−%30 arası gerçek düşüş sayılır, dokunulmaz.
    - Oran = bugünün AÇILIŞI / önceki kapanış (bölünme katsayısı, ör. 1:20 → 0.05).
      Açılış yoksa kapanış oranı kullanılır (yfinance'te Open geç boş kalabiliyor).
    - Oran (0, 0.9) aralığında olmalı; 1'e çok yakınsa bölünme değil, serbest
      düşüş/kötü veridir → atlanır. (−%30..−%90 aralığındaki gerçek düşüşler
      zaten eşik kuralıyla elenir; bu kontrol yalnızca güvenlik ağı.)

    Returns: [{'tarih': ..., 'oran': ..., 'onceki_kapanis': ..., 'acilis': ...}]
    """
    tespitler = []
    for i in range(1, len(rows)):
        onceki_k = _guvenli(rows[i - 1].get('kapanis'))
        bugun_k = _guvenli(rows[i].get('kapanis'))
        bugun_a = _guvenli(rows[i].get('acilis'))
        if not onceki_k or onceki_k <= 0 or not bugun_k or bugun_k <= 0:
            continue
        degisim = bugun_k / onceki_k - 1.0
        if degisim >= esik:          # −%30'dan küçük düşüş (yani daha az) → gerçek hareket, dokunma
            continue
        taban = bugun_a if (bugun_a and bugun_a > 0) else bugun_k
        oran = taban / onceki_k
        if not (0 < oran < 0.9):       # oran ~1 ise bölünme değil, normal düşüş/kötü veri
            continue
        tespitler.append({
            'tarih': rows[i].get('tarih'),
            'oran': round(oran, 6),
            'onceki_kapanis': round(onceki_k, 4),
            'acilis': round(taban, 4),
            'kapanis': round(bugun_k, 4),
        })
    return tespitler


def bolunme_duzelt(rows: list, tespitler: list) -> list:
    """Tespit edilen bölünmeler için ÖNCEKİ tüm barları bölünme SONRASI ölçeğe çeker — SAF fonksiyon.

    Bölünme günü ve sonrası zaten yeni (bölünmüş) birimdedir → dokunulmaz.
    Önceki barlar eski birimdedir → `× oran` (1:20 için ÷20) ile küçültülür,
    hacim ise `÷ oran` ile büyütülür. Böylece seri tek ölçekli ve sürekli olur.
    Girdi listesi değiştirilmez; yeni liste döner.
    """
    if not tespitler:
        return rows
    yeni = [dict(r) for r in rows]
    for t in tespitler:
        oran = t['oran']
        if not oran or not (0 < oran < 1):
            continue
        for r in yeni:
            if r.get('tarih', '') >= t['tarih']:   # ISO tarih → string karşılaştırma geçerli
                break
            for alan in ('acilis', 'kapanis', 'min', 'max'):
                v = _guvenli(r.get(alan))
                if v is not None:
                    r[alan] = round(v * oran, 4)
            h = _guvenli(r.get('hacim'))
            if h is not None:
                r['hacim'] = int(round(h / oran))
    return yeni


def bolunme_uygula(hisse_veri: dict) -> dict:
    """Tüm hisselere bölünme tespiti + düzeltmesi uygular.

    Returns: {sembol: [{'tarih', 'oran'}, ...]}  (saglik.bolunme_duzeltme olarak yazılır)
    """
    duzeltmeler = {}
    for sym, rows in (hisse_veri or {}).items():
        try:
            tespitler = bolunme_tespit(rows)
            if not tespitler:
                continue
            hisse_veri[sym] = bolunme_duzelt(rows, tespitler)
            duzeltmeler[sym] = [{'tarih': t['tarih'], 'oran': t['oran']} for t in tespitler]
            log(f"bölünme düzeltmesi: {sym} " +
                ", ".join(f"{t['tarih']} oran={t['oran']:.4f}" for t in tespitler))
        except Exception as e:
            log(f"bölünme düzeltme hata {sym}: {str(e)[:60]}")
    return duzeltmeler


def veri_saglik_kontrolu(hisse_veri: dict, endeks: dict | None, kaynak: str) -> dict:
    """Veri sağlık kontrolü — çapraz doğrulama (anti-hallüsinasyon).

    - Hisse sayısı yeterli mi (beklenen 100'e ne kadar yakın)
    - Yeterli barı olan hisse sayısı (>= 60 bar = indikatör hesabı mümkün)
    - Fiyat pozitifliği (0/negatif fiyat varsa bozuk veri)
    - Endeks mantıklı aralıkta mı (XU100 ~10K-100K bandı)
    """
    beklenen = 100
    toplam = len(hisse_veri)
    yeterli_bar = sum(1 for rows in hisse_veri.values() if len(rows) >= 60)
    bozuk_fiyat = sum(1 for rows in hisse_veri.values()
                      if rows and (rows[-1]['kapanis'] is None or rows[-1]['kapanis'] <= 0))
    endeks_ok = bool(endeks and 1000 <= endeks.get('deger', 0) <= 100000)
    durum = 'OK'
    sorunlar = []
    if toplam < 50:
        durum = 'KRİTİK'
        sorunlar.append(f"sadece {toplam}/{beklenen} hisse")
    elif toplam < 80:
        durum = 'UYARI'
        sorunlar.append(f"{toplam}/{beklenen} hisse")
    if yeterli_bar < 50:
        durum = 'UYARI' if durum == 'OK' else durum
        sorunlar.append(f"{yeterli_bar} hissede yeterli bar")
    if bozuk_fiyat:
        sorunlar.append(f"{bozuk_fiyat} bozuk fiyat")
    if not endeks_ok:
        sorunlar.append("endeks aralık dışı")
    return {
        'durum': durum,
        'kaynak': kaynak,
        'hisse': toplam,
        'yeterli_bar': yeterli_bar,
        'bozuk_fiyat': bozuk_fiyat,
        'endeks_ok': endeks_ok,
        'sorunlar': sorunlar,
    }


def cek_yfinance(bist_list: list) -> dict:
    """yfinance — çoklu sembol tek istekte (Actions ABD IP'den garantili çalışır)."""
    import yfinance as yf
    import pandas as pd
    tickers = [f"{s}.IS" for s in bist_list]
    veri = {}
    try:
        df = yf.download(tickers, period="1y", interval="1d",
                         group_by="ticker", auto_adjust=True, progress=False,
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
        df = yf.download("XU100.IS", period="1y", interval="1d", progress=False)
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


ONS_GRAM = 31.1034768  # 1 troy ons = 31,1034768 gram
GRAM_UYARI_ESIK = 1.0  # borsapy gram ile hesaplanan gram arası fark eşiği (%)


# ──────────────────────────────────────────────────────────────
# G05 — BIST'e özgü filtreler (saf fonksiyonlar, ağa çıkmaz)
# ──────────────────────────────────────────────────────────────
KESIN_SAAT_TR = 18.25          # 18:15 TR — bu saatten sonra üretilen sinyal "kesin"
TZ_TR = dt.timezone(dt.timedelta(hours=3))
KILIT_ESIK_PCT = 9.5           # ±%9,5 ve kapanış == uç ise tavan/taban kilidi
LIKIDITE_ESIK_TL = 50_000_000  # 20 günlük ortalama TL hacmi (kapanış × hacim) alt sınırı
LIKIDITE_PENCERE = 20
IPO_GUN = 60                   # son 60 iş günü içinde işlem görmeye başlayan = yeni halka arz
RISKLI_TABAN_SAYI = 3          # son 10 günde ≥3 taban kilidi → RISKLI
RISKLI_PENCERE = 10


def sinyal_durumu(simdi=None) -> str:
    """TR saatiyle 18:15'ten önce üretilen sinyal 'gecici', sonrası 'kesin'."""
    simdi = simdi or dt.datetime.now(dt.timezone.utc)
    tr = simdi.astimezone(TZ_TR)
    dk = tr.hour * 60 + tr.minute
    return 'kesin' if dk >= int(KESIN_SAAT_TR * 60) else 'gecici'


def kilit_tespit(row: dict, onceki_kapanis) -> str | None:
    """Tavan/taban kilidi — saf fonksiyon.

    Değişim ≥ +%9,5 ve kapanış == gün yükseği  → 'TAVAN'
    Değişim ≤ −%9,5 ve kapanış == gün düşüğü  → 'TABAN'
    Aksi halde None. row: {'kapanis','max','min'} (float veya str).
    """
    try:
        kapanis = float(str(row.get('kapanis')))
        yuksek = float(str(row.get('max')))
        dusuk = float(str(row.get('min')))
        onceki = float(str(onceki_kapanis))
    except (TypeError, ValueError):
        return None
    if not onceki or onceki <= 0:
        return None
    degisim = (kapanis / onceki - 1) * 100
    if degisim >= KILIT_ESIK_PCT and abs(kapanis - yuksek) < 1e-9:
        return 'TAVAN'
    if degisim <= -KILIT_ESIK_PCT and abs(kapanis - dusuk) < 1e-9:
        return 'TABAN'
    return None


def likidite_tl(rows: list) -> float | None:
    """20 günlük ortalama TL hacmi = ortalama(kapanış × hacim).

    Yetersiz bar varsa mevcut barlarla hesaplanır; hiç geçerli bar yoksa None.
    """
    if not rows:
        return None
    toplam, n = 0.0, 0
    for r in rows[-LIKIDITE_PENCERE:]:
        try:
            k, h = float(r.get('kapanis')), float(r.get('hacim'))
        except (TypeError, ValueError):
            continue
        if k > 0 and h >= 0:
            toplam += k * h
            n += 1
    return round(toplam / n, 0) if n else None


def ipo_bayraklari(halka_arz: list, islem_gunleri: dict, bugun=None) -> dict:
    """Son 60 iş günü içinde işlem görmeye başlayan hisseler → {SEMBOL: ilk_bar}.

    islem_gunleri: {SEMBOL: [tarih_str, ...]} (artan sıralı). İlk bar tarihi
    bugünden 60 iş günü önceki tarihten yeni ise yeni halka arz sayılır.
    """
    bugun = bugun or dt.date.today()
    esik = bugun
    sayac = 0
    while sayac < IPO_GUN:                     # 60 iş günü geriye git
        esik -= dt.timedelta(days=1)
        if esik.weekday() < 5:
            sayac += 1
    kodlar = {str(x.get('kod', '')).upper() for x in (halka_arz or []) if x.get('kod')}
    out = {}
    for sembol, tarihler in (islem_gunleri or {}).items():
        s = sembol.upper().replace('.IS', '')
        if s not in kodlar or not tarihler:
            continue
        try:
            ilk = dt.date.fromisoformat(str(tarihler[0])[:10])
        except ValueError:
            continue
        if ilk >= esik:
            out[s] = str(tarihler[0])[:10]
    return out


def taban_sayisi(rows: list, pencere: int = RISKLI_PENCERE) -> int:
    """Son `pencere` barda kaç TABAN kilidi var (kilit_tespit ile)."""
    if not rows or len(rows) < 2:
        return 0
    sayi = 0
    for i in range(max(1, len(rows) - pencere), len(rows)):
        if kilit_tespit(rows[i], rows[i - 1].get('kapanis')) == 'TABAN':
            sayi += 1
    return sayi


def riskli_tespit(rows: list) -> str | None:
    """Son 10 günde ≥3 taban kilidi → 'RISKLI' (gerekçeli), aksi halde None.

    Yakın İzleme Pazarı / konkordato bilgisi ağsız bir kaynakta güvenilir
    biçimde bulunmadığı için uydurulmaz; yalnızca ölçülebilir taban serisi
    kullanılır (G05 md.6).
    """
    n = taban_sayisi(rows)
    return f"son {RISKLI_PENCERE} günde {n} taban kilidi" if n >= RISKLI_TABAN_SAYI else None


def kilitli_gunler(rows: list) -> dict:
    """{tarih_str: 'TAVAN'|'TABAN'} — backtest giriş/çıkış kaydırması için."""
    out = {}
    for i in range(1, len(rows or [])):
        k = kilit_tespit(rows[i], rows[i - 1].get('kapanis'))
        if k:
            out[str(rows[i].get('tarih'))[:10]] = k
    return out


def ilk_kilitsiz(indeksler, kilitler: dict) -> int | None:
    """Verilen bar indekslerinde ilk kilitsiz günü döndür (yoksa None)."""
    for j in indeksler:
        if j not in kilitler:
            return j
    return None



def gram_altin_hesapla(ons_usd, usdtry, capraz, ons_kaynak=None) -> dict:
    """Gram altın = ons / 31,1034768 × USD/TL. borsapy değeri sadece 'capraz'.

    Ağa çıkmayan saf fonksiyon. ons_usd veya usdtry yoksa 'fiyat' None döner.
    capraz (borsapy) ile hesaplanan değer arasındaki fark GRAM_UYARI_ESIK'i
    aşarsa 'uyari': True olur — borsapy değeri bayat demektir.
    ons_kaynak: ons değerinin geldiği yer — 'spot' (gold-api) veya 'vadeli' (GC=F).
    """
    capraz_f = None
    try:
        capraz_f = float(capraz) if capraz is not None else None
    except (TypeError, ValueError):
        capraz_f = None

    if not ons_usd or not usdtry:
        return {'ad': 'GRAM ALTIN', 'birim': 'TL/gram', 'fiyat': None, 'degisim': None,
                'capraz': capraz_f, 'uyari': False, 'kaynak': 'ons/fx yok',
                'ons_kaynak': ons_kaynak}

    fiyat = round(float(ons_usd) / ONS_GRAM * float(usdtry), 2)
    fark = None
    uyari = False
    if capraz_f:
        fark = round((capraz_f / fiyat - 1) * 100, 2)
        uyari = abs(fark) > GRAM_UYARI_ESIK
    return {'ad': 'GRAM ALTIN', 'birim': 'TL/gram', 'fiyat': fiyat,
            'capraz': capraz_f, 'fark_yuzde': fark, 'uyari': uyari,
            'kaynak': 'ons/31,1034768 × USD/TL', 'ons_kaynak': ons_kaynak}


def spot_ons() -> float | None:
    """Canlı spot ons — gold-api.com (anahtar yok). altin_cek.spot_fiyat ile aynı yöntem."""
    try:
        req = urllib.request.Request(
            'https://api.gold-api.com/price/XAU',
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/122'})
        j = json.loads(urllib.request.urlopen(req, timeout=15).read())
        return float(j['price'])
    except Exception as e:
        log(f"spot ons hata: {str(e)[:50]}")
        return None


def makro_fiyatlar() -> dict:
    """Altın/döviz/emtia — borsapy FX (doviz.com) + ons için spot (gold-api) / GC=F.

    GRAM ALTIN: borsapy'nin gram değeri bayat olabiliyor (kanıt: 10 Kasım'da
    6.675 TL görünürken ons×USD hesabı 6.512 TL veriyordu). Bu yüzden gram
    her zaman ons / 31,1034768 × USD/TL ile hesaplanır; borsapy değeri
    'capraz' alanına yazılır ve fark %1'i aşarsa uyarı verilir.
    Ons değeri önce canlı spot'tan (gold-api.com), alınamazsa GC=F vadeli'den
    alınır ve gram kaydına 'ons_kaynak': 'spot' / 'vadeli' yazılır.
    """
    fiyatlar = {}
    borsapy_gram = None
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
                if sym == 'gram-altin':
                    borsapy_gram = float(son) if son else None
                fiyatlar[sym] = {'ad': ad, 'birim': birim, 'fiyat': round(float(son), 2) if son else None,
                                 'degisim': round((float(son) / float(acilis) - 1) * 100, 2) if son and acilis else None}
            except Exception:
                continue
    except Exception as e:
        log(f"borsapy FX hata: {str(e)[:50]}")
    # ONS altın — önce canlı spot (gold-api.com), alınamazsa yfinance GC=F
    ons_spot = spot_ons()
    ons_f, ons_deg, ons_kaynak = None, None, None
    if ons_spot:
        ons_f, ons_kaynak = round(ons_spot, 2), 'spot'
        fiyatlar['ons-altin'] = {'ad': 'ONS ALTIN', 'birim': 'USD/ons', 'fiyat': ons_f,
                                 'degisim': None, 'kaynak': 'spot'}
    try:
        import yfinance as yf
        import warnings
        warnings.filterwarnings('ignore')
        g = yf.Ticker('GC=F').history(period='5d')
        g = g.dropna()
        son = float(g['Close'].iloc[-1])
        onceki = float(g['Close'].iloc[-2]) if len(g) > 1 else son
        ons_deg = round((son / onceki - 1) * 100, 2) if onceki else None
        if ons_f is None:
            ons_f, ons_kaynak = round(son, 2), 'vadeli'
            fiyatlar['ons-altin'] = {'ad': 'ONS ALTIN', 'birim': 'USD/ons', 'fiyat': ons_f,
                                     'degisim': ons_deg, 'kaynak': 'vadeli'}
        else:
            # spot manşet; değişim yalnızca vadeli seriden (spot geçmişi yok)
            fiyatlar['ons-altin']['degisim'] = ons_deg
            fiyatlar['ons-altin']['vadeli_fiyat'] = round(son, 2)
    except Exception as e:
        log(f"ons altın hata: {str(e)[:50]}")
    # GRAM ALTIN — her zaman ons/USD'den hesaplanır (borsapy gram bayat olabiliyor)
    try:
        usd_f = (fiyatlar.get('USD') or {}).get('fiyat')
        usd_deg = (fiyatlar.get('USD') or {}).get('degisim')
        gram = gram_altin_hesapla(ons_f, usd_f, borsapy_gram, ons_kaynak)
        if ons_deg is not None and usd_deg is not None and gram.get('fiyat'):
            # bileşik değişim: (1+ons)(1+usd) - 1
            gram['degisim'] = round(((1 + ons_deg / 100) * (1 + usd_deg / 100) - 1) * 100, 2)
        fiyatlar['gram-altin'] = gram
        if gram.get('uyari'):
            log(f"gram altın UYARI: borsapy {gram.get('capraz')} vs hesap {gram.get('fiyat')} "
                f"(fark %{gram.get('fark_yuzde')})")
    except Exception as e:
        log(f"gram altın hesap hata: {str(e)[:50]}")
    # VIX + emtialar — yfinance (küresel risk iştahı + sektörel ipucu)
    ekstra = [
        ('^VIX', 'VIX KORKU', 'seviye', True),   # ters: artış = korku = kırmızı
        ('NG=F', 'DOĞALGAZ', 'USD', False),
        ('HG=F', 'BAKIR', 'USD/lb', False),
        ('ZW=F', 'BUĞDAY', 'USc/buşel', False),
    ]
    for sym, ad, birim, ters in ekstra:
        try:
            import yfinance as yf
            import warnings
            warnings.filterwarnings('ignore')
            h = yf.Ticker(sym).history(period='5d').dropna()
            if h.empty:
                continue
            son = float(h['Close'].iloc[-1])
            onceki = float(h['Close'].iloc[-2]) if len(h) > 1 else son
            fiyatlar[sym] = {'ad': ad, 'birim': birim, 'fiyat': round(son, 2),
                             'degisim': round((son / onceki - 1) * 100, 2) if onceki else None,
                             'ters': ters}
        except Exception as e:
            log(f"{ad} hata: {str(e)[:40]}")
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


def sinyalleri_hesapla(hisse_veri: dict, ipo: dict | None = None) -> dict:
    """OHLCV verisinden indikatör + sinyal hesapla (indikatorler.py mantığı).

    G05 filtreleri (saf, ağsız):
      - durum        : 'gecici' (18:15 TR öncesi) / 'kesin'
      - kilit        : 'TAVAN' / 'TABAN' — o gün tavan/taban kilidi
      - likidite_tl  : 20 günlük ortalama TL hacmi
      - ipo_yeni     : son 60 iş gününde işlem görmeye başladı (skor istatistiğinden hariç)
      - tedbir       : VBTS tedbiri (kaynak yoksa None — uydurulmaz)
      - riskli       : AL yerine 'RISKLI' (son 10 günde ≥3 taban)
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from indikatorler import tum_indikatorler, sinyal_hesapla, pivot_seviyeler, seviye_durumu, ict_sinyalleri
    import pandas as pd

    durum = sinyal_durumu()
    ipo = ipo or {}
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
                # ── G05 filtre alanları ──
                'durum': durum,
                'likidite_tl': likidite_tl(rows),
                'ipo_yeni': sembol in ipo,
                'tedbir': None,
                **({'ipo_tarih': ipo[sembol]} if sembol in ipo else {}),
            })
        except Exception:
            continue
    # G05 — kilit / likidite / riskli / IPO filtresi (sinyal üretiminden sonra uygulanır)
    for r in sonuclar:
        rows = hisse_veri.get(r['sembol']) or []
        r['kilit'] = kilit_tespit(rows[-1], rows[-2].get('kapanis')) if len(rows) > 1 else None
        risk = riskli_tespit(rows)
        r['riskli'] = risk
        r['taban_10g'] = taban_sayisi(rows)
        if r['sinyal'] in ('AL', 'DİKKAT_AL'):
            if risk:                                    # md.6 — sorunlu hisse
                r['sinyal'], r['sinyal_ham'], r['filtre'] = 'RISKLI', r['sinyal'], risk
            elif r.get('tedbir'):                       # md.5 — VBTS
                r['sinyal'], r['sinyal_ham'], r['filtre'] = 'IZLE', r['sinyal'], 'VBTS tedbiri'
            elif r.get('likidite_tl') is not None and r['likidite_tl'] < LIKIDITE_ESIK_TL:
                r['sinyal'], r['sinyal_ham'], r['filtre'] = 'IZLE', r['sinyal'], 'likidite eşiği altı'
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
    # G05 md.4 — yeni halka arzlar skor istatistiklerinden hariç
    istatistik_kaynak = [r for r in sonuclar if not r.get('ipo_yeni') and not r.get('riskli')]
    skorlar = [r['skor'] for r in istatistik_kaynak]
    return {
        '_tum': sonuclar,   # kırpılmamış tam kesit — sektör/gece/karne/log bunu kullanır, JSON'a yazılmaz
        'al': [r for r in sonuclar if r['sinyal'] in ('AL', 'DİKKAT_AL')][:15],
        'tut': [r for r in sonuclar if r['sinyal'] == 'TUT'][:10],
        'sat': [r for r in sonuclar if r['sinyal'] in ('SAT', 'DİKKAT_SAT')][:10],
        'izle': [r for r in sonuclar if r['sinyal'] == 'IZLE'][:15],
        'riskli': [r for r in sonuclar if r['sinyal'] == 'RISKLI'][:15],
        'tarama': tarama,
        'toplam': len(sonuclar),
        'durum': durum,
        'hesap_tarihi': dt.datetime.now().strftime('%d.%m.%Y %H:%M'),
        'filtre_esikleri': {'kilit_pct': KILIT_ESIK_PCT, 'likidite_tl': LIKIDITE_ESIK_TL,
                            'ipo_gun': IPO_GUN, 'taban_10g': RISKLI_TABAN_SAYI},
        'skor_istatistik': {'kapsam': len(istatistik_kaynak),
                            'haric': len(sonuclar) - len(istatistik_kaynak),
                            'ort_skor': round(sum(skorlar) / len(skorlar), 2) if skorlar else None},
    }


def ict_tara(hisse_veri: dict) -> dict:
    """ICT TARAYICI — tüm BIST hisselerinde tam ICT setini çalıştır (Katman 2).

    Mantık kaynağı: ArunKBhaskar/PineScript (ICT MSS/FVG/OB/Mitigation/EQH-EQL/Void/
    Market Profile/Displacement) → Python'a çevrildi (scripts/ict.py).
    Skor kuralları ict.py başlığında açık; burada sadece tarama + toplama yapılır.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from ict import ict_hesapla
    import pandas as pd

    mss_up, mss_dn, fvg_acik, ob_ici = [], [], [], []
    sweep, eqh, eql, alim, satim = [], [], [], [], []
    islenen = 0
    for sembol, rows in hisse_veri.items():
        if not rows or len(rows) < 40:
            continue
        try:
            df = pd.DataFrame(rows)
            df = df.rename(columns={'tarih': 'date', 'kapanis': 'close', 'acilis': 'open',
                                    'min': 'low', 'max': 'high', 'hacim': 'volume'})
            df = df.sort_values('date').reset_index(drop=True)
            r = ict_hesapla(df)
        except Exception:
            continue
        if not r:
            continue
        islenen += 1
        fiyat = r.get('fiyat')
        m = r.get('mss') or {}
        if m.get('yon') == 'BULLISH':
            mss_up.append({'sembol': sembol, 'fiyat': fiyat, 'seviye': m['seviye'], 'aciklama': m['aciklama']})
        elif m.get('yon') == 'BEARISH':
            mss_dn.append({'sembol': sembol, 'fiyat': fiyat, 'seviye': m['seviye'], 'aciklama': m['aciklama']})
        f = r.get('fvg') or {}
        if f and f.get('durum') == 'AÇIK':
            fvg_acik.append({'sembol': sembol, 'yon': f['yon'], 'alt': f['alt'], 'ust': f['ust'],
                             'konum': f['konum'], 'fiyat': fiyat})
        o = r.get('ob') or {}
        if o and o.get('durum') == 'İÇİNDE':
            ob_ici.append({'sembol': sembol, 'yon': o['yon'], 'alt': o['alt'], 'ust': o['ust'], 'fiyat': fiyat})
        s = r.get('sweep') or {}
        if s.get('yon'):
            sweep.append({'sembol': sembol, 'yon': s['yon'], 'seviye': s['seviye'], 'aciklama': s['aciklama']})
        if r.get('eqh'):
            eqh.append({'sembol': sembol, 'seviye': r['eqh']['seviye']})
        if r.get('eql'):
            eql.append({'sembol': sembol, 'seviye': r['eql']['seviye']})
        kayit = {'sembol': sembol, 'fiyat': fiyat, 'skor': r['skor'],
                 'sinyal': r['sinyal'], 'nedenler': r['nedenler']}
        if r['sinyal'] == 'AL':
            alim.append(kayit)
        elif r['sinyal'] == 'SAT':
            satim.append(kayit)

    alim.sort(key=lambda x: x['skor'], reverse=True)
    satim.sort(key=lambda x: x['skor'])
    return {
        'mss_yukari': mss_up[:20],
        'mss_asagi': mss_dn[:20],
        'fvg_acik': fvg_acik[:20],
        'ob_ici': ob_ici[:20],
        'sweep': sweep[:20],
        'eqh': eqh[:20],
        'eql': eql[:20],
        'al': alim[:15],
        'sat': satim[:15],
        'islenen': islenen,
        'al_sayisi': len(alim),
        'sat_sayisi': len(satim),
        'hesap_tarihi': dt.datetime.now().strftime('%d.%m.%Y %H:%M'),
        'kural': ('MSS ±2, displacement ±1, fiyat FVG/OB bölgesi içinde ±1, likidite süpürmesi ±1, '
                  'değer alanı dışı ±1. Skor ≥3 AL, ≤-3 SAT.'),
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
        # G05 — kilitli günler (tavan/taban): o gün ne giriş ne çıkış yapılabilir
        kilitler = {}
        for k in range(1, len(ind)):
            kk = kilit_tespit({'kapanis': ind.iloc[k]['HGDG_KAPANIS'], 'max': ind.iloc[k]['HGDG_MAX'],
                               'min': ind.iloc[k]['HGDG_MIN']}, ind.iloc[k - 1]['HGDG_KAPANIS'])
            if kk:
                kilitler[k] = kk
        for i in range(60, len(ind) - 1):
            son = ind.iloc[i]
            s = sinyal_hesapla(son)
            if s['sinyal'] not in ('AL', 'DİKKAT_AL'):
                continue
            giris_gunu = pd.Timestamp(son['HGDG_TARIH']).date()
            # G05 — kilitli günde giriş yapılmaz, ilk kilitsiz güne kaydırılır
            gi = ilk_kilitsiz(range(i + 1, len(ind)), kilitler)
            if gi is None:
                continue
            sonraki = ind.iloc[gi]
            giris_fiyat = float(sonraki['HGDG_ACILIS']) if pd.notna(sonraki.get('HGDG_ACILIS')) else float(sonraki['HGDG_KAPANIS'])
            if not giris_fiyat or giris_fiyat <= 0:
                continue
            getiri = (son_fiyat / giris_fiyat - 1) * 100
            # S3: stop-loss kontrolü — girişten sonraki barlarda -%5'e düştü mü?
            # G05 md.6 — taban kilitli günde çıkış yapılamaz (stop-loss dahil), ilk kilitsiz güne kaydırılır
            stop_calismadi = True
            stop_getiri = getiri
            for j in range(gi, len(ind) + 1):
                if j >= len(ind):
                    break
                if kilitler.get(j) == 'TABAN':
                    continue
                d_ip = (float(ind.iloc[j]['HGDG_MIN']) / giris_fiyat - 1) * 100
                if d_ip <= -5:
                    stop_calismadi = False
                    stop_getiri = -5.0  # %5 stop ile çıkıldı
                    break
            islem = {'sembol': sembol, 'tarih': str(giris_gunu), 'giris_tarih': str(pd.Timestamp(sonraki['HGDG_TARIH']).date()),
                     'giris': round(giris_fiyat, 2),
                     'bugun': round(son_fiyat, 2), 'getiri_yuzde': round(getiri, 1),
                     'stop_getiri_yuzde': round(stop_getiri, 1), 'stop_calismis': not stop_calismadi,
                     'sinyal_tarih': str(son['HGDG_TARIH'].date()),
                     'kaydirildi': gi != i + 1, 'kilit': kilitler.get(gi),
                     'skor': int(s['skor'])}
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
            # Alan adı: aslında "en kötü işlem getirisi" (pozitif olabilir).
            # Eski ad 'max_dusus' bir sürüm boyunca geriye uyumluluk için yazılır.
            'en_kotu_islem': round(min(getiriler), 1),
            'max_dusus': round(min(getiriler), 1),
        })
    hisse_ozet.sort(key=lambda x: x['toplam_getiri'], reverse=True)

    # 2.4 — 100K TL sermaye simülasyonu (eski sürüm özelliği):
    # SKOR≥3 strateji: güçlü AL sinyalleri, 10.000 TL/pozisyon, max 10 pozisyon
    # (100K/10K) → toplam tahsis asla başlangıcı aşmaz (tutarlı). Pozisyonlar
    # bugüne kadar tutulur; stop varyantı -%5'te kapatır. Gerçek getirilerden.
    def sermaye(islemler, stop_mu=False, baslangic=100000.0, tahsis=10000.0):
        guclu = [x for x in islemler if x.get('skor', 0) >= 3]
        if not guclu:  # skor≥3 yoksa en güçlü sinyaller (DİKKAT_AL dahil) — boş kalmaz
            guclu = sorted(islemler, key=lambda x: -x.get('skor', 0))[:10]
        guclu = guclu[:int(baslangic / tahsis)]  # max 10 pozisyon
        if not guclu:
            return {'baslangic': baslangic, 'sonuc': baslangic, 'kar_zarar': 0.0,
                    'islem': 0, 'tahsis': tahsis, 'strateji': 'skor≥3'}
        toplam = baslangic
        for x in guclu:
            g = x['stop_getiri_yuzde'] if stop_mu else x['getiri_yuzde']
            toplam += tahsis * g / 100.0
        return {'baslangic': baslangic, 'sonuc': round(toplam, 0),
                'kar_zarar': round(toplam - baslangic, 0),
                'islem': len(guclu), 'tahsis': tahsis, 'strateji': 'skor≥3'}

    return {
        'pazartesi_acilis': ozetle(pazartesi_islemleri, 'Pazartesi açılışında al'),
        'ertesi_gun_acilis': ozetle(gunluk_islemler, 'Sinyal ertesi gün açılışında al'),
        'stop_losslu': ozetle(gunluk_islemler, 'Ertesi gün açılış + %5 stop-loss', stop_mu=True),
        'hisse_bazli': hisse_ozet[:20],
        'sermaye': {
            'pazartesi': sermaye(pazartesi_islemleri),
            'ertesi': sermaye(gunluk_islemler),
            'stop': sermaye(gunluk_islemler, stop_mu=True),
        },
        'aciklama': ('Senaryolar GERÇEK veriyle hesaplanır: sinyal günü kapanışında AL/DİKKAT_AL üreten '
                     'hisse, ertesi gün açılıştan alınır ve bugünkü kapanışla kar/zarar ölçülür. '
                     'Stop-loss senaryosu giriş sonrası -%5 düşüşte çıkış varsayar.'),
    }


def haber_tarihi_iso(deger) -> str | None:
    """Herhangi bir yayın tarihi biçimini UTC ISO'ya çevir. Ağa çıkmaz.

    Desteklenen biçimler:
      - RFC-2822 / "+0000 GMT" (email.utils.parsedate_to_datetime)
      - ISO 8601 ("2026-11-11T14:03:00Z", "+03:00" ofsetli, ofsetsiz)
      - "YYYY-MM-DD HH:MM:SS" (ofsetsiz → UTC kabul edilir)
      - "YYYY-MM-DD"
    Ayrıştırılamazsa None döner (uydurma tarih yazılmaz).
    """
    import datetime as _dt
    from email.utils import parsedate_to_datetime

    if deger is None:
        return None
    s = str(deger).strip()
    if not s:
        return None

    # 1) RFC-2822 ("Wed, 11 Nov 2026 14:03:00 +0000" / "... GMT")
    try:
        dt = parsedate_to_datetime(s)
    except (TypeError, ValueError, IndexError):
        dt = None
    if dt is not None:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
        return dt.astimezone(_dt.timezone.utc).isoformat()

    # 2) ISO 8601
    t = s.replace('Z', '+00:00').replace('z', '+00:00')
    try:
        dt = _dt.datetime.fromisoformat(t)
    except ValueError:
        dt = None
    if dt is not None:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc)  # ofsetsiz → UTC kabul
        return dt.astimezone(_dt.timezone.utc).isoformat()

    # 3) Açık biçimler
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            dt = _dt.datetime.strptime(s[:len(fmt) + 4], fmt).replace(tzinfo=_dt.timezone.utc)
            return dt.astimezone(_dt.timezone.utc).isoformat()
        except ValueError:
            continue
    return None


def _rss_cek(url: str, limit: int = 12) -> list:
    """RSS feed çek — stdlib (xml.etree) + httpx. pubDate → ISO normalize."""
    try:
        import httpx
        from xml.etree import ElementTree as ET
        from email.utils import parsedate_to_datetime
        r = httpx.get(url, timeout=15, follow_redirects=True, headers=HEADERS)
        if r.status_code != 200 or '<item>' not in r.text:
            return []
        root = ET.fromstring(r.text)
        sonuc = []
        for item in root.findall('.//item')[:limit]:
            baslik = (item.findtext('title') or '').strip()
            if not baslik:
                continue
            link = (item.findtext('link') or '').strip()
            pub = (item.findtext('pubDate') or '').strip()
            iso = haber_tarihi_iso(pub) if pub else None
            sonuc.append({'baslik': baslik[:200], 'link': link, 'pub': iso})
        return sonuc
    except Exception:
        return []


def _dil_tespit(baslik: str, varsayilan: str = 'en') -> str:
    """Türkçe karakter varsa tr, yoksa kaynak varsayılanı."""
    tr_karakter = any(c in baslik.lower() for c in 'ğışöüç')
    return 'tr' if tr_karakter else varsayilan


_EKLER = ('', 'ı', 'i', 'u', 'ü', 'ın', 'in', 'un', 'ün', 'ını', 'ini', 'unu', 'ünü', 'a', 'e',
         'da', 'de', 'ta', 'te', 'dan', 'den', 'tan', 'ten', 'lar', 'ler', 'ları', 'leri', 'nda', 'nde')


def _tr_lower(m: str) -> str:
    return m.replace('İ', 'i').replace('I', 'ı').lower()


def _kelime_var(tokenler, kok: str) -> bool:
    """Kısa köklerde (≤4 harf) sadece kök+izinli ek eşleşir: 'kar' → 'karı' evet, 'karar' HAYIR.
    Uzun köklerde önek eşleşmesi yeterli: 'yükseldi' → 'yükseldiğini'."""
    if len(kok) <= 4:
        return any(t == kok + e for t in tokenler for e in _EKLER)
    return any(t.startswith(kok) for t in tokenler)


def _yon_etiket(baslik: str) -> tuple:
    """Anahtar kelime kurallarıyla yön + etiket (LLM'siz, uydurma yok).
    Önce çok kelimeli ifadeler (bağlam), sonra tek kelimeler kelime sınırıyla."""
    pozitif_kw = ['kâr', 'kar', 'temettü', 'temettu', 'sözleşme', 'sozlesme', 'ihale', 'yatırım',
                  'büyüme', 'buyume', 'rekor', 'anlaşma', 'anlasma', 'kazanç', 'kazanc', 'yükseldi',
                  'yukseldi', 'profit', 'dividend', 'contract', 'award', 'growth', 'record',
                  'agreement', 'upgrade', 'beat']
    negatif_kw = ['zarar', 'dava', 'ceza', 'soruşturma', 'sorusturma', 'istifa', 'iflas', 'konkordato',
                  'düşüş', 'dusus', 'düştü', 'dustu', 'kayıp', 'kayip', 'kriz', 'yaptırım', 'yaptirim',
                  'savaş', 'savas', 'loss', 'lawsuit', 'investigation', 'resign', 'bankruptcy',
                  'decline', 'probe', 'downgrade', 'miss']
    ifade_neg = ['faiz artış', 'faiz artir', 'faiz artır', 'zarar açıkla', 'not indir', 'kredi notunu düşür']
    ifade_poz = ['faiz indir', 'not artır', 'kredi notunu yükselt', 'kâr açıkla', 'kar açıkla']
    alt = _tr_lower(baslik)
    poz = sum(1 for k in ifade_poz if k in alt)
    neg = sum(1 for k in ifade_neg if k in alt)
    for k in ifade_poz + ifade_neg:
        alt = alt.replace(k, ' ')
    tokenler = re.findall(r"[0-9a-zçğıöşüâîû]+", alt)
    poz += sum(1 for k in pozitif_kw if _kelime_var(tokenler, k))
    neg += sum(1 for k in negatif_kw if _kelime_var(tokenler, k))
    if poz > neg:
        return 'pozitif', '🟢 Pozitif'
    if neg > poz:
        return 'negatif', '🔴 Negatif'
    return 'notr', '⚪ Nötr'


def haberler_cek(oncelikli_hisseler=None) -> list:
    """Cryptopanic tarzı çok kaynaklı haber akışı — BIST + global + makro + altın.

    Kaynaklar (hepsi key'siz, Actions ABD IP'de çalışır):
    - Yahoo Finance: BIST hisseleri (bist) + GC=F altın / SI=F gümüş (altin-maden)
    - Habertürk Ekonomi RSS (makro, tr)
    - FortuneTR RSS (makro, tr)
    - CNBC Economy RSS (makro, en)
    - CNBC Top News RSS (global, en)
    - Investing.com RSS (global, en)

    Her haber: baslik, kaynak, kategori, dil, yon/etiket, yayin_tarihi (ISO).
    Sıralama: yeniden eskiye. Son 7 gün filtresi.
    """
    import yfinance as yf
    import warnings
    import datetime as _dt
    warnings.filterwarnings('ignore')

    haberler = []
    gorulen = set()  # aynı başlığı tekrar ekleme

    def ekle(baslik, kaynak, kategori, dil, sembol='', link='', pub=None):
        if not baslik or len(baslik) < 15:
            return
        anahtar = baslik.lower()[:80]
        if anahtar in gorulen:
            return
        gorulen.add(anahtar)
        yon, etiket = _yon_etiket(baslik)
        iso = haber_tarihi_iso(pub) if pub else None
        haberler.append({
            'baslik': baslik[:180], 'kaynak': kaynak, 'kategori': kategori,
            'dil': dil, 'yon': yon, 'etiket': etiket, 'sembol': sembol,
            'link': link, 'yayin_tarihi': iso,
            'tarih': (iso or '')[:10] if iso else '',
        })

    # 1) BIST hisseleri (Yahoo) — mevcut mantık
    oncelikli = oncelikli_hisseler or ['THYAO', 'AKBNK', 'ASELS', 'GARAN', 'ISCTR', 'KCHOL',
                                       'SAHOL', 'TUPRS', 'EREGL', 'BIMAS']
    for sym in oncelikli:
        try:
            t = yf.Ticker(f"{sym}.IS")
            for n in (t.news or [])[:3]:
                c = n.get('content', {})
                baslik = c.get('title', '')
                if not baslik:
                    continue
                iso = haber_tarihi_iso(c.get('pubDate'))
                yayinci = (c.get('provider') or {}).get('displayName', 'Yahoo')
                ekle(baslik, yayinci, 'bist', _dil_tespit(baslik, 'en'), sym, '', iso)
        except Exception:
            continue

    # 2) Altın / Gümüş (Yahoo — GC=F, SI=F)
    for sembol, kategori in [('GC=F', 'altin-maden'), ('SI=F', 'altin-maden')]:
        try:
            t = yf.Ticker(sembol)
            for n in (t.news or [])[:4]:
                c = n.get('content', {})
                baslik = c.get('title', '')
                if not baslik:
                    continue
                iso = haber_tarihi_iso(c.get('pubDate'))
                yayinci = (c.get('provider') or {}).get('displayName', 'Yahoo')
                ekle(baslik, yayinci, kategori, _dil_tespit(baslik, 'en'), sembol, '', iso)
        except Exception:
            continue

    # 3) RSS kaynakları
    rss_kaynaklari = [
        ('https://www.haberturk.com/rss/ekonomi.xml', 'Habertürk', 'makro', 'tr'),
        ('https://www.fortuneturkey.com/rss', 'Fortune TR', 'makro', 'tr'),
        ('https://www.paratic.com/feed/', 'Paratic', 'makro', 'tr'),
        ('https://www.bloomberght.com/rss', 'Bloomberg HT', 'bist', 'tr'),
        ('https://www.cnbc.com/id/10001147/device/rss/rss.html', 'CNBC Ekonomi', 'makro', 'en'),
        ('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'CNBC Dünya', 'global', 'en'),
        ('https://www.investing.com/rss/news.rss', 'Investing.com', 'global', 'en'),
        # Google News arama akışları — KAP bildirimleri + TR borsa + global makro (key'siz)
        ('https://news.google.com/rss/search?q=KAP+bildirim+duyuru&hl=tr&gl=TR&ceid=TR:tr', 'Google News · KAP', 'bist', 'tr'),
        ('https://news.google.com/rss/search?q=borsa+istanbul+ekonomi&hl=tr&gl=TR&ceid=TR:tr', 'Google News · TR Borsa', 'bist', 'tr'),
        ('https://news.google.com/rss/search?q=fed+inflation+china+markets&hl=en&gl=US&ceid=US:en', 'Google News · Global', 'global', 'en'),
    ]
    for url, kaynak, kategori, dil in rss_kaynaklari:
        for item in _rss_cek(url, limit=12):
            ekle(item['baslik'], kaynak, kategori, dil, '', item.get('link', ''), item.get('pub'))

    # 4) Tarihe göre yeniden eskiye sırala (filtre yok — eski haberler de görünsün,
    #    zaman damgası "X ay önce" olarak gösterilir; max 100 haber)
    haberler.sort(key=lambda x: x['yayin_tarihi'] or '', reverse=True)
    return haberler[:100]


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


def tam_kesit_log(tum: list, endeks: dict | None, kaynak: str) -> None:
    """data/log/YYYY-MM.jsonl — her işlem günü için BİR satır (gün içi çalışmalar aynı günü
    üzerine yazar → günün son satırı = kapanış durumu). 100 hisse × ~12 alan ≈ 12 KB/gün.

    Bu dosya sinyal denetiminin (scripts/sinyal_denetim.py --log data/log) temelidir:
    kırpılmış AL/SAT listeleri yerine TÜM evren kaydedilir → seçim yanlılığı olmadan
    ileri getiri, IC ve skor kovası analizi yapılabilir.
    """
    if not tum:
        return
    gun = max(r['tarih'] for r in tum)
    alanlar = ('sembol', 'tarih', 'fiyat', 'skor', 'sinyal', 'trend', 'rsi', 'mfi', 'macd_hist',
               'squeeze', 'ay_oncesi', 'stop', 'hedef')
    satir = {'t': utc_now_iso(), 'gun': gun, 'kaynak': kaynak, 'endeks': endeks,
             'rows': [{k: r.get(k) for k in alanlar} for r in tum if r.get('tarih') == gun]}
    log_dir = DATA_DIR / 'log'
    log_dir.mkdir(exist_ok=True)
    f = log_dir / f"{gun[:7]}.jsonl"
    eski = []
    if f.exists():
        eski = [l for l in f.read_text(encoding='utf-8').splitlines()
                if l.strip() and json.loads(l).get('gun') != gun]
    eski.append(json.dumps(satir, ensure_ascii=False, separators=(',', ':')))
    f.write_text('\n'.join(eski) + '\n', encoding='utf-8')
    log(f"tam kesit log: {f.name} · {gun} · {len(satir['rows'])} hisse")


def gece_analizi(sinyaller: dict, takvim: list) -> dict:
    """5 — Kapanış sonrası özet: yarının kritik seviyeleri + güçlü/zayıf adaylar.

    Tüm veri mevcut hesaplardan türetilir (uydurma yok):
    - En güçlü AL (skor ≥ 3) ve en zayıf SAT (skor ≤ -3) adayları
    - Bollinger sıkışmadakiler (kırılım izlenecek)
    - Aşırı satımlar (RSI < 30)
    - Yarının yüksek önemli makro olayları
    """
    hepsi = sinyaller.get('_tum') or (sinyaller.get('al', []) + sinyaller.get('tut', []) + sinyaller.get('sat', []))
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

    # 1. Hisse verisi — 3 kademeli failover (patron önerisi):
    #    1) İş Yatırım (TR IP — en hızlı, gerçek zamanlı)
    #    2) borsapy TradingView provider (İş Yatırım'dan bağımsız, global)
    #    3) yfinance (garanti fallback)
    hisse_veri = cek_isyatirim(liste)
    kaynak = "isyatirim"
    if not hisse_veri:
        log("İş Yatırım başarısız → borsapy (TradingView) deneniyor")
        hisse_veri = cek_borsapy(liste)
        kaynak = "borsapy-tv"
    if not hisse_veri:
        log("borsapy başarısız → yfinance deneniyor")
        hisse_veri = cek_yfinance(liste)
        kaynak = "yfinance"
    if not hisse_veri:
        log("KRİTİK: TÜM KAYNAKLAR BAŞARISIZ")
        hisse_veri = {}

    # 1b. Bölünme (split) düzeltmesi — veri çekildikten HEMEN sonra, hiçbir analizden önce.
    #     Düzeltilmemiş bölünme MA/RSI/ATR, backtest ve ICT sonuçlarını bozar (ör. RALYH −%98).
    bolunme_duzeltmeleri = {}
    if hisse_veri:
        try:
            bolunme_duzeltmeleri = bolunme_uygula(hisse_veri)
            log(f"Bölünme düzeltmesi: {len(bolunme_duzeltmeleri)} hisse"
                + (f" — {', '.join(sorted(bolunme_duzeltmeleri))}" if bolunme_duzeltmeleri else ""))
        except Exception as e:
            log(f"bölünme düzeltmesi hata: {str(e)[:60]}")

    # 2. Endeks
    endeks = endeks_verisi()

    # 2b. Veri sağlık kontrolü (çapraz doğrulama)
    saglik = veri_saglik_kontrolu(hisse_veri or {}, endeks, kaynak)
    saglik['bolunme_duzeltme'] = [{'sembol': s, **t}
                                  for s in sorted(bolunme_duzeltmeleri)
                                  for t in bolunme_duzeltmeleri[s]]
    log(f"SAĞLIK: {saglik['durum']} | kaynak={kaynak} | hisse={saglik['hisse']} | "
        f"yeterli_bar={saglik['yeterli_bar']} | sorunlar={saglik['sorunlar']}")

    # 3. Makro
    fiyatlar = makro_fiyatlar()
    takvim = takvim_cek()
    faiz = tcmb_faizi()
    tufe = tufe_verisi()

    # 4. Sinyaller (G05 — yeni halka arz bayrakları: takvim.json'daki halka_arz + ilk bar tarihleri)
    halka_arz = []
    try:
        with open(DATA_DIR / 'takvim.json', encoding='utf-8') as f:
            halka_arz = json.load(f).get('halka_arz') or []
    except Exception:
        halka_arz = []
    islem_gunleri = {s: [str(r.get('tarih'))[:10] for r in (rows or []) if r.get('tarih')]
                     for s, rows in (hisse_veri or {}).items()}
    ipo = ipo_bayraklari(halka_arz, islem_gunleri)
    if ipo:
        log(f"G05: yeni halka arz = {len(ipo)} ({', '.join(sorted(ipo))})")
    sinyaller = sinyalleri_hesapla(hisse_veri, ipo) if hisse_veri else {'al': [], 'tut': [], 'sat': [], 'izle': [], 'riskli': [], 'toplam': 0, 'hesap_tarihi': ''}

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
    tum = sinyaller.get('_tum') or (sinyaller.get('al', []) + sinyaller.get('tut', []) + sinyaller.get('sat', []))
    for r in tum:
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
    guncel_fiyatlar = {r['sembol']: r['fiyat'] for r in tum}   # tam kesit → survivorship yok
    sinyal_gecmisi = sinyal_gecmisi_ozet(gecmis, guncel_fiyatlar)

    # 5g. Gece analizi (madde 5)
    gece = gece_analizi(sinyaller, takvim)

    # 5h. ICT TARAYICI (Katman 2 — PineScript mantığı: MSS/FVG/OB/sweep/EQH-EQL/Profile)
    ict_tarama = ict_tara(hisse_veri) if hisse_veri else {}
    log(f"ICT tarayıcı: {ict_tarama.get('islenen', 0)} hisse işlendi | "
        f"AL={ict_tarama.get('al_sayisi', 0)} SAT={ict_tarama.get('sat_sayisi', 0)} | "
        f"MSS↑{len(ict_tarama.get('mss_yukari', []))} MSS↓{len(ict_tarama.get('mss_asagi', []))} "
        f"OB-içi={len(ict_tarama.get('ob_ici', []))}")

    log(f"Haberler: {len(haberler)} | Fonlar: {len(fonlar.get('fonlar', []))} | "
        f"Sektör: {len(sektor_list)} | Temel analiz: {len(temel)} | "
        f"Doğruluk: {sinyal_gecmisi.get('toplam')} sinyal")

    # 5i. Tam kesit günlük log (sinyal denetimi için)
    try:
        tam_kesit_log(tum, endeks, kaynak)
    except Exception as e:
        log(f"tam kesit log hata: {str(e)[:60]}")
    sinyaller.pop('_tum', None)

    # 6. JSON yaz
    paket = {
        'uretildi': utc_now_iso(),
        'kaynak': kaynak,
        'saglik': saglik,
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
        'ict_tarama': ict_tarama,
    }
    (DATA_DIR / 'piyasa.json').write_text(json.dumps(paket, ensure_ascii=False, indent=1), encoding='utf-8')
    log(f"piyasa.json yazıldı: {os.path.getsize(DATA_DIR / 'piyasa.json')} byte")
    log("=== TAMAM ===")


if __name__ == '__main__':
    main()
