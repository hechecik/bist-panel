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
import json, os, sys, re, time
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

# ══════════════════════════════════════════════════════════════════════════
# G05 — BIST'e özgü filtre eşikleri (ayarlanabilir parametreler)
# ══════════════════════════════════════════════════════════════════════════
LIKIDITE_ESIK_TL = 50_000_000   # 20 günlük ortalama TL hacmi (kapanış × hacim) alt sınırı
LIKIDITE_PENCERE = 20           # likidite ortalaması için geriye bakılan bar sayısı
KILIT_ESIK_PCT = 9.5            # ±%9,5 ve kapanış == uç ise tavan/taban kilidi
RISKLI_TABAN_SAYI = 3           # son RISKLI_PENCERE günde ≥3 taban kilidi → RISKLI
RISKLI_PENCERE = 10
IPO_GUN = 60                    # son 60 iş günü içinde işlem görmeye başlayan = yeni halka arz
KESIN_SAAT_TR = 18.5            # 18:30 TR — borsa 18:10 kapanır ama ücretsiz kaynaklar ~15 dk gecikmeli
KESIN_DK_TR = 18 * 60 + 30      # 18:30 TR (dakika)

# ══════════════════════════════════════════════════════════════════════════
# G08 — Backtest parametreleri (dosya başında, tek yerden ayarlanır)
# ══════════════════════════════════════════════════════════════════════════
MALIYET = 0.002                 # gidiş-dönüş işlem maliyeti (0,002 = %0,2) — net getiriden düşülür
BT_VADE_GUN = (5, 10, 20)       # işlem günü vadeleri — ilk dolan vade çıkış olur
BT_ATR_STOP = 2.0               # stop = giriş − 2×ATR (giriş gününden önceki barın ATR14'ü)
BT_ATR_HEDEF = 3.0              # hedef = giriş + 3×ATR
BT_SERMAYE = 100_000.0          # sermaye simülasyonu başlangıç (TL)
BT_MAX_POZISYON = 10            # aynı anda açık pozisyon üst sınırı


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


def cek_borsapy(bist_list: list, nedenler: dict | None = None) -> dict:
    """2. KADEME — borsapy TradingView provider (İş Yatırım'dan BAĞIMSIZ).

    borsapy Ticker.history() kendi calendar.py çakışması yüzünden bug'li —
    provider doğrudan kullanılır. TradingView global olduğu için Actions
    ABD IP'sinde de çalışır. Tek istek/hisse (~1 sn) — 100 hisse ~2 dk.

    `nedenler` verilirse düşen her hisse için sebep yazılır (LOG_NEDEN_*):
    zaman aşımı, boş yanıt, az bar, sembol hatası. Her sembol 2 kez denenir.
    """
    try:
        from borsapy._providers.tradingview import get_tradingview_provider
        import pandas as pd
    except Exception:
        return {}
    veri = {}
    try:
        p = get_tradingview_provider()
    except Exception as e:
        log(f"borsapy (TradingView) provider hata: {str(e)[:60]}")
        return veri
    for sym in bist_list:
        son_hata = None
        for _deneme in range(2):          # ilk tur düşen hisse ikinci kez denenir
            try:
                df = p.get_history(sym, interval='1d', period='1y')  # SMA200 için ≥200 bar şart
                if df is None or len(df) < 60:
                    son_hata = (LOG_NEDEN_BOS_YANIT if df is None
                                else f"{LOG_NEDEN_AZ_BAR} ({len(df)} bar)")
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
                    son_hata = None
                    break
                son_hata = f"{LOG_NEDEN_BOS_YANIT} (boş bar)"
            except Exception as e:
                son_hata = f"{LOG_NEDEN_SEMBOL}: {type(e).__name__}: {str(e)[:70]}"
                if _deneme == 0:
                    time.sleep(1)
        if sym not in veri and son_hata and nedenler is not None:
            nedenler[sym] = son_hata
            log(f"borsapy DÜŞTÜ {sym}: {son_hata}")
    log(f"borsapy (TradingView) OK: {len(veri)}/{len(bist_list)} hisse")
    return veri


def cek_yfinance_tek(sembol: str) -> list:
    """TEK hisse yfinance (.IS) — hisse bazlı tamamlama. Hatada (None, sebep) döner."""
    try:
        import yfinance as yf
        import pandas as pd
    except Exception as e:
        return None, f"{LOG_NEDEN_SEMBOL}: yfinance import: {str(e)[:60]}"
    t = f"{sembol}.IS"
    try:
        df = yf.download(t, period="1y", interval="1d", progress=False,
                         auto_adjust=True, threads=False)
    except Exception as e:
        return None, f"{LOG_NEDEN_SEMBOL}: yfinance {type(e).__name__}: {str(e)[:70]}"
    if df is None or df.empty:
        return None, LOG_NEDEN_BOS_YANIT
    try:
        if isinstance(df.columns, pd.MultiIndex):
            df = df.xs(t, axis=1, level="Ticker")
        sub = df.dropna(subset=['Close'])
        rows = []
        for idx, row in sub.iterrows():
            k = float(row['Close'])
            if k != k or k <= 0:
                continue
            rows.append({
                'tarih': str(pd.Timestamp(idx).date()),
                'kapanis': round(k, 4),
                'acilis': round(float(row['Open']), 4) if row['Open'] == row['Open'] else None,
                'min': round(float(row['Low']), 4) if row['Low'] == row['Low'] else None,
                'max': round(float(row['High']), 4) if row['High'] == row['High'] else None,
                'hacim': int(row['Volume']) if row['Volume'] == row['Volume'] else None,
            })
    except Exception as e:
        return None, f"{LOG_NEDEN_BOS_YANIT}: parse: {str(e)[:60]}"
    if len(rows) < 60:
        return None, f"{LOG_NEDEN_AZ_BAR} ({len(rows)} bar)"
    return rows, None


def tamamla_yfinance(hisse_veri: dict, kalan: list, nedenler: dict | None = None) -> tuple:
    """borsapy'den gelmeyen hisseleri SADECE onları yfinance (.IS) ile tekrar çeker.

    Her tamamlanan hissenin satırlarına `kaynak='yfinance'` alanı yazılır
    (kaynak izlenebilirliği). `nedenler` sözlüğü tamamlanamayanların
    gerekçesiyle güncellenir.
    Returns: (eklenen_liste, hala_eksik_liste)
    """
    kalan = [s for s in kalan if s not in hisse_veri]
    if not kalan:
        return [], []
    log(f"Tamamlama: {len(kalan)} hisse yfinance (.IS) ile tek tek çekiliyor: "
        f"{', '.join(kalan)}")
    eklenen, hala_yok = [], []
    for sym in kalan:
        rows, neden = cek_yfinance_tek(sym)
        if rows:
            for r in rows:
                r['kaynak'] = 'yfinance'
            hisse_veri[sym] = rows
            eklenen.append(sym)
            log(f"  tamamlandı {sym}: yfinance {len(rows)} bar")
        else:
            hala_yok.append(sym)
            if nedenler is not None:
                nedenler[sym] = neden or "bilinmeyen"
            log(f"  TAMAMLANAMADI {sym}: {neden or 'bilinmeyen'}")
    log(f"Tamamlama sonucu: {len(eklenen)} eklendi "
        f"({', '.join(eklenen) if eklenen else 'yok'}) | kalan eksik: {len(hala_yok)}")
    return eklenen, hala_yok


# ══════════════════════════════════════════════════════════════════════════
# Eksik hisse teşhisi — düşme nedenleri (log'da görünür olmalı, anti-hallüsinasyon)
# ══════════════════════════════════════════════════════════════════════════
LOG_NEDEN_BOS_YANIT = "boş yanıt"        # kaynak hisse için hiç bar döndürmedi
LOG_NEDEN_AZ_BAR = "az bar"              # dönen bar sayısı indikatör için yetersiz
LOG_NEDEN_SEMBOL = "sembol/istisna"      # sembol hatası veya kaynak istisnası (timeout dahil)

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


def veri_saglik_kontrolu(hisse_veri: dict, endeks: dict | None, kaynak: str,
                         eksik_hisseler: list | None = None,
                         eksik_nedenler: dict | None = None) -> dict:
    """Veri sağlık kontrolü — çapraz doğrulama (anti-hallüsinasyon).

    - Hisse sayısı yeterli mi (beklenen 100'e ne kadar yakın)
    - Yeterli barı olan hisse sayısı (>= 60 bar = indikatör hesabı mümkün)
    - Fiyat pozitifliği (0/negatif fiyat varsa bozuk veri)
    - Endeks mantıklı aralıkta mı (XU100 ~10K-100K bandı)
    - Kaynak dağılımı (borsapy / yfinance / isyatirim) — şeffaflık
    - eksik_hisseler: hiç verisi gelemeyen semboller + nedeni
    """
    beklenen = 100
    toplam = len(hisse_veri)
    yeterli_bar = sum(1 for rows in hisse_veri.values() if len(rows) >= 60)
    bozuk_fiyat = sum(1 for rows in hisse_veri.values()
                      if rows and (rows[-1]['kapanis'] is None or rows[-1]['kapanis'] <= 0))
    endeks_ok = bool(endeks and 1000 <= endeks.get('deger', 0) <= 100000)
    eksik_hisseler = list(eksik_hisseler or [])
    eksik_nedenler = dict(eksik_nedenler or {})
    # Kaynak dağılımı: son barın 'kaynak' alanına göre (hisse bazlı tamamlama izlenebilirliği)
    kaynak_dagilim = {}
    for rows in hisse_veri.values():
        k = (rows[-1].get('kaynak') if rows else None) or 'bilinmiyor'
        kaynak_dagilim[k] = kaynak_dagilim.get(k, 0) + 1
    durum = 'OK'
    sorunlar = []
    if toplam < 50:
        durum = 'KRİTİK'
        sorunlar.append(f"sadece {toplam}/{beklenen} hisse")
    elif toplam < 100 or eksik_hisseler:
        # Patron kuralı: 100'ün altındaysa UYARI + isim listesi görünür olmalı
        durum = 'UYARI'
        if toplam < 100:
            sorunlar.append(f"{toplam}/{beklenen} hisse")
    if yeterli_bar < 50:
        durum = 'UYARI' if durum == 'OK' else durum
        sorunlar.append(f"{yeterli_bar} hissede yeterli bar")
    if bozuk_fiyat:
        sorunlar.append(f"{bozuk_fiyat} bozuk fiyat")
    if not endeks_ok:
        sorunlar.append("endeks aralık dışı")
    if eksik_hisseler:
        detay = ", ".join(f"{s}({eksik_nedenler.get(s, 'bilinmiyor')})"
                          for s in eksik_hisseler[:10])
        sorunlar.append(f"{len(eksik_hisseler)} hisse çekilemedi: {detay}")
    return {
        'durum': durum,
        'kaynak': kaynak,
        'hisse': toplam,
        'beklenen': beklenen,
        'yeterli_bar': yeterli_bar,
        'bozuk_fiyat': bozuk_fiyat,
        'endeks_ok': endeks_ok,
        'kaynak_dagilim': kaynak_dagilim,
        'eksik_hisseler': eksik_hisseler,
        'eksik_nedenler': eksik_nedenler,
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
    """BIST 100 endeks — yfinance XU100.IS (^XU100.IS sembolü Yahoo'da yok).

    G09: eski alanlar (deger/degisim_yuzde/tarih) AYNEN korunur; RS20/RS60 için
    tam kapanış serisi `seri` (tarih→kapanış) ve `seri_son` (son 80 gün) eklendi.
    """
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
        kapanis = df['Close'].dropna()
        return {
            'deger': round(float(son['Close']), 2),
            'degisim_yuzde': round((float(son['Close']) / float(onceki['Close']) - 1) * 100, 2),
            'tarih': str(df.index[-1].date()),
            # G09 — tam seri (gölge mod: sadece RS hesabı için okunur)
            'seri': [[str(ix.date()), round(float(v), 2)] for ix, v in kapanis.items()],
            'seri_son': [round(float(v), 2) for v in kapanis.iloc[-80:]],
        }
    except Exception as e:
        log(f"Endeks hata: {str(e)[:60]}")
        return None


ONS_GRAM = 31.1034768  # 1 troy ons = 31,1034768 gram
GRAM_UYARI_ESIK = 1.0  # borsapy gram ile hesaplanan gram arası fark eşiği (%)


# ──────────────────────────────────────────────────────────────
# G05 — BIST'e özgü filtreler (saf fonksiyonlar, ağa çıkmaz)
# Eşikler dosyanın başında tanımlı: LIKIDITE_ESIK_TL, KILIT_ESIK_PCT, ...
# ──────────────────────────────────────────────────────────────
TZ_TR = dt.timezone(dt.timedelta(hours=3))


def sinyal_durumu(bar_tarihi=None, simdi=None) -> str:
    """Sinyalin kesinlik durumu — saf fonksiyon, ağa çıkmaz.

    Kural (TR takvim günü bazlı):
      - bar_tarihi bugünden önceyse → 'kesin' (bar kapanmış, gün bitmiş)
      - bar_tarihi bugünse → TR 18:30 ve sonrası 'kesin', öncesi 'gecici'

    Saate tek başına bakmak yanlıştı: sabah 09:07 çalışması dünün kapanmış
    barını işler ve tatil günlerinde de bar eskidir; bunlar kesin sayılmalı.

    bar_tarihi: date/datetime/ISO string ('2026-11-11' veya '2026-11-11T...').
                None verilirse 'bugün' varsayılır (yalnızca saat kuralı işler).
    """
    simdi = simdi or dt.datetime.now(dt.timezone.utc)
    tr = simdi.astimezone(TZ_TR)
    if bar_tarihi is not None:
        b = _tr_gun(bar_tarihi)
        if b is not None:
            if b < tr.date():
                return 'kesin'
            if b > tr.date():
                return 'gecici'   # gelecek tarihli bar — henüz oluşmadı
    dk = tr.hour * 60 + tr.minute
    return 'kesin' if dk >= KESIN_DK_TR else 'gecici'


def _tr_gun(deger):
    """Tarih benzeri değeri TR takvim gününe (date) çevirir — saf yardımcı."""
    if deger is None:
        return None
    if isinstance(deger, dt.datetime):
        d = deger
        if d.tzinfo is not None:
            d = d.astimezone(TZ_TR)
        return d.date()
    if isinstance(deger, dt.date):
        return deger
    s = str(deger).strip()
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


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


def uygun_evren(rows: list, bugun=None) -> tuple:
    """(uygun, neden, ilk_bar_tarihi) — backtest/istatistik evreni filtresi.

    Yeni halka arz (ilk bar son 60 iş günü içinde) istatistik dışıdır (G05 md.4).
    Etiketi RISKLI olan hisse ayrıca `riskli_tespit` ile dışlanır (çağıran taraf).
    Ağa çıkmayan saf fonksiyon.
    """
    if not rows:
        return False, 'veri yok', None
    ilk = str(rows[0].get('tarih'))[:10]
    bugun = bugun or dt.date.today()
    esik = bugun
    sayac = 0
    while sayac < IPO_GUN:
        esik -= dt.timedelta(days=1)
        if esik.weekday() < 5:
            sayac += 1
    try:
        ilk_d = dt.date.fromisoformat(ilk)
    except ValueError:
        return True, None, ilk
    if ilk_d >= esik:
        return False, f'yeni halka arz (ilk bar {ilk})', ilk
    return True, None, ilk


def _hafta_gunu(tarih_str):
    """ISO tarih → hafta günü (0=pazartesi); ayrıştırılamazsa None."""
    try:
        return dt.date.fromisoformat(str(tarih_str)[:10]).weekday()
    except (TypeError, ValueError):
        return None


def _bar_fiyat(bar, alan: str):
    """Bar alanını float'a çevir; geçersizse None."""
    try:
        v = float(bar[alan])
    except (KeyError, TypeError, ValueError):
        return None
    return v if v > 0 else None


def _islem_hesapla(sembol: str, i: int, s: dict, ind, kilitler: dict) -> dict | None:
    import pandas as pd  # noqa: F401 — yerel import (modül düzeyinde pandas yok)
    """Tek sinyal → tek işlem (G08 kuralları).

    Giriş: sinyalin ERTESİ günü açılış; kilitli günde ilk kilitsiz güne kayar (G05).
    Çıkış: 5/10/20 iş günü vade VEYA 2×ATR stop / 3×ATR hedef — hangisi önce.
      • Stop ve hedef GÜN İÇİ min/max ile kontrol edilir.
      • Aynı gün ikisi de tetiklenirse STOP sayılır (muhafazakâr).
      • Taban kilitli günde çıkış ilk kilitsiz güne kayar.
    Maliyet (MALIYET, gidiş-dönüş) net getiriden düşülür.
    Dönüş: işlem sözlüğü; `_cikis_i` geçici alan çağıran tarafından silinir.
    """
    n = len(ind)
    si = i                                  # sinyal barı
    gi = ilk_kilitsiz(range(si + 1, n), kilitler)
    if gi is None:
        return None
    giris_fiyat = _bar_fiyat(ind.iloc[gi], 'HGDG_ACILIS') or _bar_fiyat(ind.iloc[gi], 'HGDG_KAPANIS')
    if not giris_fiyat:
        return None

    # ATR: sinyal barındaki ATR14 (giriş günü kararından önce bilinen değer)
    try:
        atr14 = float(ind.iloc[si]['ATR14'])
    except (KeyError, TypeError, ValueError):
        atr14 = 0.0
    if not atr14 or atr14 <= 0:
        atr14 = giris_fiyat * 0.02          # ATR yoksa %2 varsayılan (nadir)
    stop_fiyat = giris_fiyat - BT_ATR_STOP * atr14
    hedef_fiyat = giris_fiyat + BT_ATR_HEDEF * atr14

    # En uzun vade: işlem günü sayısı (kilitli günler de işlem günüdür, sadece işlem yapılamaz)
    vade_son = {}
    sayac = 0
    for j in range(gi, n):
        sayac += 1
        if sayac in BT_VADE_GUN:
            vade_son[sayac] = j
    if not vade_son:
        return None
    son_j = max(vade_son.values())

    cikis_i, cikis_fiyat, cikis_neden = None, None, None
    for j in range(gi, son_j + 1):
        kilit = kilitler.get(j)
        # Taban kilitli günde hiçbir çıkış yapılamaz (G05 md.6) — ilk kilitsiz güne kayar
        if kilit == 'TABAN':
            continue
        dusuk = _bar_fiyat(ind.iloc[j], 'HGDG_MIN')
        yuksek = _bar_fiyat(ind.iloc[j], 'HGDG_MAX')
        stop_vurdu = dusuk is not None and dusuk <= stop_fiyat
        hedef_vurdu = yuksek is not None and yuksek >= hedef_fiyat
        if stop_vurdu:                      # aynı gün ikisi de → STOP (muhafazakâr)
            cikis_i, cikis_fiyat, cikis_neden = j, stop_fiyat, 'stop'
            break
        if hedef_vurdu:
            cikis_i, cikis_fiyat, cikis_neden = j, hedef_fiyat, 'hedef'
            break
        if j in vade_son.values():
            cikis_i, cikis_fiyat, cikis_neden = j, (_bar_fiyat(ind.iloc[j], 'HGDG_KAPANIS') or giris_fiyat), 'vade'
            break
    if cikis_i is None:                     # vade sonu da kilitliydi → sonraki ilk kilitsiz gün
        cikis_i = ilk_kilitsiz(range(son_j + 1, n), kilitler)
        if cikis_i is None:
            return None
        cikis_fiyat = _bar_fiyat(ind.iloc[cikis_i], 'HGDG_KAPANIS') or giris_fiyat
        cikis_neden = 'vade'

    brut = (cikis_fiyat / giris_fiyat - 1) * 100
    # Gidiş-dönüş maliyet: alışta (1+MALIYET/2), satışta (1−MALIYET/2) uygulanır
    net = (cikis_fiyat * (1 - MALIYET / 2)) / (giris_fiyat * (1 + MALIYET / 2)) * 100 - 100
    # Stop durumunda da aynı mantık: stop fiyatından satış, maliyetli giriş fiyatına göre
    stop_net = (stop_fiyat * (1 - MALIYET / 2)) / (giris_fiyat * (1 + MALIYET / 2)) * 100 - 100
    return {
        'sembol': sembol,
        'tarih': str(pd.Timestamp(ind.iloc[si]['HGDG_TARIH']).date()),      # geriye uyum
        'sinyal_tarih': str(pd.Timestamp(ind.iloc[si]['HGDG_TARIH']).date()),
        'giris_tarih': str(pd.Timestamp(ind.iloc[gi]['HGDG_TARIH']).date()),
        'cikis_tarih': str(pd.Timestamp(ind.iloc[cikis_i]['HGDG_TARIH']).date()),
        'giris': round(giris_fiyat, 2),
        'cikis': round(cikis_fiyat, 2),
        'bugun': round(cikis_fiyat, 2),                                      # geriye uyum
        'getiri_yuzde': round(net, 1),                                       # net (maliyet düşülmüş)
        'brut_getiri_yuzde': round(brut, 1),
        'maliyet_yuzde': round(MALIYET * 100, 2),
        'stop_getiri_yuzde': round(stop_net, 1),
        'stop_calismis': cikis_neden == 'stop',
        'kaydirildi': gi != si + 1,
        'kilit': kilitler.get(gi),
        'skor': int(s['skor']),
        'cikis_neden': cikis_neden,
        'vade_gun': sum(1 for j in range(gi, cikis_i + 1)),
        'atr': round(atr14, 3), 'stop_fiyat': round(stop_fiyat, 2), 'hedef_fiyat': round(hedef_fiyat, 2),
        '_cikis_i': cikis_i,
    }


def sermaye_simule(islemler: list, baslangic=None, max_pozisyon=None) -> dict:
    """KRONOLOJİK sermaye simülasyonu (G08).

    100.000 TL, en fazla `max_pozisyon` eşzamanlı pozisyon, slot başına
    baslangic/max_pozisyon TL. Nakit/slot yoksa sinyal ATLANIR.
    Getiriler işlem bazında yüzde; giriş/çıkış tarihleri kronolojik sıralanır.
    """
    baslangic = float(BT_SERMAYE if baslangic is None else baslangic)
    max_pozisyon = int(BT_MAX_POZISYON if max_pozisyon is None else max_pozisyon)
    tahsis = baslangic / max_pozisyon if max_pozisyon else baslangic

    # Aynı giriş tarihli sinyallerde SKOR azalan, eşitlikte sembol (deterministik)
    sira = sorted(islemler, key=lambda x: (x.get('giris_tarih') or '',
                                           -(x.get('skor') or 0),
                                           x.get('sembol') or ''))
    sermaye = baslangic
    acik = []                                # [(cikis_tarih, getiri_yuzde, tahsis_tl)]
    atlanan = 0
    islenen = 0
    beklenen_kar = 0.0                       # Σ(tahsis × getiri/100) — mutabakat için
    zirve, max_dd = baslangic, 0.0

    for x in sira:
        giris_t = x.get('giris_tarih') or ''
        # O güne kadar çıkanları kapat, parayı geri ekle
        kalan = []
        for cikis_t, g, tutar in acik:
            if cikis_t <= giris_t:
                sermaye += tutar * (1 + g / 100.0)
            else:
                kalan.append((cikis_t, g, tutar))
        acik = kalan
        if len(acik) >= max_pozisyon or sermaye < tahsis:
            atlanan += 1
            continue
        sermaye -= tahsis
        acik.append((x.get('cikis_tarih') or giris_t, x.get('getiri_yuzde', 0.0), tahsis))
        beklenen_kar += tahsis * x.get('getiri_yuzde', 0.0) / 100.0
        islenen += 1
        # Eşit ağırlıklı anlık portföy değeri (açık pozisyonlar maliyetten sayılır)
        deger = sermaye + len(acik) * tahsis
        zirve = max(zirve, deger)
        if zirve > 0:
            max_dd = max(max_dd, (zirve - deger) / zirve * 100)

    for _cikis_t, g, tutar in acik:
        sermaye += tutar * (1 + g / 100.0)
    kar_zarar = sermaye - baslangic
    fark = kar_zarar - beklenen_kar
    return {'baslangic': baslangic, 'sonuc': round(sermaye, 0),
            'kar_zarar': round(kar_zarar, 0), 'islem': islenen,
            'atlanan': atlanan, 'tahsis': round(tahsis, 0),
            'gerceklesen_max_dd_yuzde': round(max_dd, 1),
            'max_drawdown_yuzde': round(max_dd, 1),   # geriye uyum (bir sürüm)
            'beklenen_kar': round(beklenen_kar, 0),
            'mutabakat_fark': round(fark, 0),
            'mutabakat_fark_yuzde': round(fark / baslangic * 100, 3)}



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


# ══════════════════════════════════════════════════════════════════════════
# G13 — Reel BIST (USD / gram altın bazlı) + Türkiye risk kartı
# Saf fonksiyonlar (ağa çıkmaz) — ağ erişimi yalnız `tr_risk_blogu()` içinde.
# ══════════════════════════════════════════════════════════════════════════

# Pencereler İŞ GÜNÜ (bar) cinsinden — 1h=5, 1a=21, 3a=63, 1y=252 bar.
G13_DONEM_BAR = {'1h': 5, '1a': 21, '3a': 63, '1y': 252}
# Tarihe göre hizalama toleransı (gün). Seride hedef tarih yoksa en yakın ÖNCEKİ
# tarih kullanılır; tolerans aşılırsa o değer "veri yok" sayılır (eski veri taşınmaz).
G13_TOLERANS_GUN = 7
G13_TUTARLILIK_TOL_PCT = 0.1          # TL/USD/altın tutarlılık testi eşiği (±%0,1)
ONS_GRAM_G13 = 31.1034768

TR_AYLAR = {'ocak': 1, 'şubat': 2, 'subat': 2, 'mart': 3, 'nisan': 4, 'mayıs': 5, 'mayis': 5,
            'haziran': 6, 'temmuz': 7, 'ağustos': 8, 'agustos': 8, 'eylül': 9, 'eylul': 9,
            'ekim': 10, 'kasım': 11, 'kasim': 11, 'aralık': 12, 'aralik': 12}


def _g13_tarih(deger) -> dt.date:
    """'2026-11-11' / date / datetime → date (saat dilimi farkı yaratmadan)."""
    if isinstance(deger, dt.datetime):
        return deger.date()
    if isinstance(deger, dt.date):
        return deger
    return dt.date.fromisoformat(str(deger)[:10])


def _g13_sayi(v):
    """float'a çevir; geçersizse None (uydurma yok)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None          # NaN → None


def seri_eslestir(ana_seri, *diger_seriler, tolerans=G13_TOLERANS_GUN):
    """Saf fonksiyon: serileri TARİHE göre hizala (index ile DEĞİL).

    G11'deki `tarihe_gore_deger` yaklaşımının yeniden kullanımı: ana serinin her
    tarihi için diğer serilerde en yakın ÖNCEKİ değer aranır (hafta sonu/tatil
    boşlukları tolere edilir). Tolerans aşılırsa o gün eşleşmez.

    Girdi: ana_seri=[(tarih, değer), ...] ve diğer seriler aynı biçimde.
    Dönüş: [(tarih, [değer, ...]), ...] — yalnız TÜM serileri eşleşen günler,
    eskiden yeniye. Ana serinin kendi değeri None ise gün atlanır.
    """
    seriler = []
    for s in diger_seriler:
        temiz = [(_g13_tarih(t), _g13_sayi(v)) for t, v in (s or []) if _g13_sayi(v) is not None]
        temiz.sort(key=lambda x: x[0])
        seriler.append(temiz)
    out = []
    ana = sorted(((_g13_tarih(t), _g13_sayi(v)) for t, v in (ana_seri or [])), key=lambda x: x[0])
    for t, v in ana:
        if v is None:
            continue
        degerler = [v]
        for s in seriler:
            aday = None
            for ts, vs in s:
                if ts <= t:
                    aday = (ts, vs)
                else:
                    break
            if aday is None or (t - aday[0]).days > tolerans:
                break
            degerler.append(aday[1])
        if len(degerler) != len(seriler) + 1:
            continue
        out.append((t, degerler))
    return out


def _g13_hedef_tarih(son: dt.date, bar: int) -> dt.date:
    """`bar` iş günü geriye ≈ takvim günü (×7/5, yukarı yuvarlanır)."""
    return son - dt.timedelta(days=int(bar * 7 / 5 + 0.999))


def _g13_baz(hizali, hedef: dt.date, tolerans=G13_TOLERANS_GUN):
    """Hizalı seride hedef tarihe en yakın ÖNCEKİ günü bul."""
    aday = None
    for t, vals in hizali:
        if t <= hedef:
            aday = (t, vals)
        else:
            break
    if aday is None or (hedef - aday[0]).days > tolerans:
        return None
    return aday


def reel_bist_serileri(xu100_seri, usdtry_seri, gram_seri):
    """Saf fonksiyon: XU100 / USDTRY ve XU100 / gram altın serileri (tarihe göre hizalı).

    Girdiler [(tarih, kapanış), ...]. Dönüş {'tl','usd','altin': [(tarih, değer)],
    'bas','son','hizalama'} — üç seri de AYNI gün kümesine sahiptir.
    """
    hizali = seri_eslestir(xu100_seri, usdtry_seri, gram_seri)
    tl, usd, altin = [], [], []
    for t, (x, u, g) in hizali:
        if not x or not u or not g:
            continue
        tl.append((t.isoformat(), round(x, 2)))
        usd.append((t.isoformat(), round(x / u, 4)))
        altin.append((t.isoformat(), round(x / g, 4)))
    if not tl:
        return {'durum': 'veri yok', 'tl': [], 'usd': [], 'altin': [],
                'hizalama': {'eslesen_gun': 0}}
    return {'durum': 'ok', 'tl': tl, 'usd': usd, 'altin': altin,
            'bas': tl[0][0], 'son': tl[-1][0],
            'hizalama': {'eslesen_gun': len(tl), 'yontem': 'tarihe göre en yakın önceki gün',
                         'tolerans_gun': G13_TOLERANS_GUN}}


def _g13_getiri(seri, son_t: dt.date, hedef_t: dt.date, tolerans=G13_TOLERANS_GUN):
    """Tek seri için yüzde getiri (hedef → son). Eşleşme yoksa None."""
    son = _g13_baz(seri, son_t, 0)
    if son is None or son[0] != son_t:
        return None
    bas = _g13_baz(seri, hedef_t, tolerans)
    if son is None or bas is None or bas[0] == son[0] or not bas[1]:
        return None
    return {'pct': round((son[1] / bas[1] - 1) * 100, 3), 'bas_tarih': bas[0].isoformat(),
            'son_tarih': son[0].isoformat(), 'bas_deger': round(float(bas[1]), 4),
            'son_deger': round(float(son[1]), 4),
            'kaydirma_gun': (hedef_t - bas[0]).days}


def reel_bist_getirileri(seriler: dict, bugun=None) -> dict:
    """Saf fonksiyon: 1h/1a/3a/1y/YBB getirileri — TL / USD / altın bazında.

    `seriler`: reel_bist_serileri() çıktısı. Pencereler İŞ GÜNÜ: 1h=5, 1a=21, 3a=63, 1y=252 bar.
    YBB = yılbaşından beri (son yılın ilk işlem günü).
    Tutarlılık: (1+TL)/(1+USDTRY değ.)−1 ≈ USD getirisi (tutarlılık bloğunda).
    """
    if not seriler or seriler.get('durum') != 'ok':
        return {'durum': 'veri yok', 'donemler': {}}
    tl = [(_g13_tarih(t), v) for t, v in seriler['tl']]
    usd = [(_g13_tarih(t), v) for t, v in seriler['usd']]
    altin = [(_g13_tarih(t), v) for t, v in seriler['altin']]
    son_t = tl[-1][0]
    yilbasi = dt.date(son_t.year, 1, 1)
    ybb_baz = None
    for t, _v in tl:
        if t.year == son_t.year:
            ybb_baz = t
            break

    donemler = {}
    for kod, bar in G13_DONEM_BAR.items():
        hedef = _g13_hedef_tarih(son_t, bar)
        satir = {'bar': bar, 'hedef_tarih': hedef.isoformat(), 'not': '1y için 252 bar ≈ takvim yılı'}
        eksik = []
        for ad, s in (('tl', tl), ('usd', usd), ('altin', altin)):
            g = _g13_getiri(s, son_t, hedef)
            if g is None:
                eksik.append(ad)
                satir[ad] = None
            else:
                satir[ad] = g['pct']
                satir[f'{ad}_bas_tarih'] = g['bas_tarih']
        satir['bas_tarih'] = satir.get('tl_bas_tarih')
        if eksik:
            satir['eksik'] = eksik
            satir['not'] = 'seri geçmişi yetmiyor — ' + ', '.join(eksik) + ' için veri yok'
        donemler[kod] = satir

    ybb = {'bar': None, 'hedef_tarih': yilbasi.isoformat(), 'yilbasi': True}
    if ybb_baz is None or ybb_baz >= son_t:
        ybb.update({'tl': None, 'usd': None, 'altin': None, 'durum': 'veri yok'})
    else:
        ybb['bas_tarih'] = ybb_baz.isoformat()
        for ad, s in (('tl', tl), ('usd', usd), ('altin', altin)):
            g = _g13_getiri(s, son_t, ybb_baz)
            ybb[ad] = g['pct'] if g else None
            if g:
                ybb[f'{ad}_bas_tarih'] = g['bas_tarih']
        if ybb.get('tl') is None:
            ybb['durum'] = 'veri yok'
    ybb['yilbasi_str'] = ybb_baz.isoformat() if ybb_baz else None
    donemler['ybb'] = ybb

    return {'durum': 'ok', 'son_tarih': son_t.isoformat(), 'donemler': donemler,
            'tutarlilik': reel_bist_tutarlilik(donemler, seriler, son_t)}


def reel_bist_tutarlilik(donemler: dict, seriler: dict, son_t: dt.date) -> list:
    """Saf fonksiyon: (1+TL)/(1+USDTRY değişimi)−1 ≈ USD getirisi (±%0,1) kontrolü.

    USDTRY değişimi XU100/USDTRY serisinden TÜRETİLMEZ; ham kur serisi oransal
    olarak yeniden hesaplanır: kur_oran = (TL baz değeri / USD baz değeri) oranı.
    """
    sonuclar = []
    tl = [(_g13_tarih(t), v) for t, v in seriler['tl']]
    usd = [(_g13_tarih(t), v) for t, v in seriler['usd']]
    for kod, d in (donemler or {}).items():
        if not isinstance(d, dict):
            continue
        if d.get('tl') is None or d.get('usd') is None or not d.get('bas_tarih'):
            sonuclar.append({'donem': kod, 'durum': 'veri yok'})
            continue
        bas = _g13_tarih(d['bas_tarih'])
        tl_son = _g13_baz(tl, son_t, 0)
        tl_bas = _g13_baz(tl, bas, 0)
        usd_son = _g13_baz(usd, son_t, 0)
        usd_bas = _g13_baz(usd, bas, 0)
        if not all((tl_son, tl_bas, usd_son, usd_bas)):
            sonuclar.append({'donem': kod, 'durum': 'veri yok'})
            continue
        # ima edilen USDTRY değişimi = (TL/USD oranı) — oran = XU100 / (XU100/USDTRY)
        kur_oran = (tl_son[1] / usd_son[1]) / (tl_bas[1] / usd_bas[1])
        beklenen = ((1 + d['tl'] / 100) / kur_oran - 1) * 100
        fark = beklenen - d['usd']
        sonuclar.append({'donem': kod, 'beklenen_usd_pct': round(beklenen, 3),
                         'usd_pct': d['usd'], 'fark_pct': round(fark, 4),
                         'esik_pct': G13_TUTARLILIK_TOL_PCT,
                         'ok': abs(fark) <= G13_TUTARLILIK_TOL_PCT})
    return sonuclar


# ── Türkiye risk kartı ────────────────────────────────────────────────────

def reel_faiz(politika_faizi, yillik_tufe):
    """Saf fonksiyon: reel faiz = politika faizi − yıllık TÜFE (puan). Eksik girdi → None."""
    p, t = _g13_sayi(politika_faizi), _g13_sayi(yillik_tufe)
    if p is None or t is None:
        return None
    return round(p - t, 2)


def tahvil_getirileri(getiri_json: dict):
    """Saf fonksiyon: getiri.json'dan TR 2Y/10Y. Yoksa {'durum': 'veri yok'} — uydurma yok."""
    rows = (getiri_json or {}).get('tahvil') or []
    out = {}
    for r in rows:
        vade = str((r or {}).get('vade') or '').upper()
        g = _g13_sayi((r or {}).get('getiri'))
        if vade in ('2Y', '10Y') and g is not None:
            out[vade] = g
    blok = {'2Y': out.get('2Y'), '10Y': out.get('10Y'),
            'durum': (getiri_json or {}).get('tahvil_durum') or ('ok' if out else 'veri yok'),
            'kaynak': (getiri_json or {}).get('kaynak')}
    eksik = [k for k in ('2Y', '10Y') if out.get(k) is None]
    if eksik:
        blok['eksik'] = eksik
        blok['not'] = 'getiri.json tahvil verisi boş/eksik: ' + ', '.join(eksik)
    return blok


def ppk_tarihleri_parse(html: str, yil: int):
    """Saf fonksiyon: TCMB PPK sayfası HTML → karar tarihleri (ISO), artan sıralı.

    Sayfada "Para Politikası Kurulu Toplantı Kararı" tablosu vardır; ilk sütun
    KARAR tarihidir. Yalnız `yil` yılına ait satırlar alınır. Tarih uydurulmaz —
    tablo yoksa boş liste döner.
    """
    if not html:
        return []
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        import re as _re
        desen = _re.compile(r'(\d{1,2})\s*(Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|Haziran|Temmuz|'
                            r'Ağustos|Agustos|Eylül|Eylul|Ekim|Kasım|Kasim|Aralık|Aralik)\s*(\d{4})',
                            _re.IGNORECASE)
        bulunan = set()
        for m in desen.finditer(html.replace('&nbsp;', ' ')):
            ay = TR_AYLAR.get(m.group(2).lower())
            if ay and int(m.group(3)) == yil:
                try:
                    bulunan.add(dt.date(int(m.group(3)), ay, int(m.group(1))).isoformat())
                except ValueError:
                    continue
        return sorted(bulunan)
    soup = BeautifulSoup(html, 'html.parser')
    tarihler = set()
    for tr in soup.find_all('tr'):
        hucreler = tr.find_all(['td', 'th'])
        if not hucreler:
            continue
        metin = hucreler[0].get_text(' ', strip=True).replace('\xa0', ' ')
        m = re.match(r'^(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})$', metin)
        if not m:
            continue
        ay = TR_AYLAR.get(m.group(2).lower())
        if not ay or int(m.group(3)) != yil:
            continue
        try:
            tarihler.add(dt.date(yil, ay, int(m.group(1))).isoformat())
        except ValueError:
            continue
    return sorted(tarihler)


def sonraki_ppk(tarihler: list, bugun=None):
    """Saf fonksiyon: bugünden SONRAKİ ilk PPK karar tarihi + geri sayım (takvim günü)."""
    bugun = bugun or dt.date.today()
    bugun = _g13_tarih(bugun)
    for t in sorted(tarihler or []):
        try:
            tt = _g13_tarih(t)
        except ValueError:
            continue
        if tt >= bugun:
            return {'tarih': tt.isoformat(), 'kalan_gun': (tt - bugun).days}
    return {'durum': 'veri yok', 'not': 'tarihler arasında bugünden sonraki PPK yok'}


def ppk_sayfa_url(yil: int) -> str:
    return ('https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Temel+Faaliyetler/'
            f'Para+Politikasi/PPK/{yil}')


def ppk_takvimi(bugun=None) -> dict:
    """Ağ: TCMB PPK sayfaları (bu yıl + gelecek yıl) → tarihler + sonraki toplantı."""
    bugun = _g13_tarih(bugun or dt.date.today())
    tum, hatalar, kaynak = [], [], []
    try:
        import httpx
    except ImportError:
        return {'durum': 'veri yok', 'hata': 'httpx yok'}
    for yil in (bugun.year, bugun.year + 1):
        try:
            r = httpx.get(ppk_sayfa_url(yil), timeout=25, follow_redirects=True, headers=HEADERS)
            if r.status_code != 200:
                hatalar.append(f'{yil}: HTTP {r.status_code}')
                continue
            t = ppk_tarihleri_parse(r.text, yil)
            if t:
                tum.extend(t)
                kaynak.append(ppk_sayfa_url(yil))
            else:
                hatalar.append(f'{yil}: tablo bulunamadı')
        except Exception as e:
            hatalar.append(f'{yil}: {str(e)[:60]}')
    tum = sorted(set(tum))
    blok = {'tarihler': tum, 'kaynak': kaynak[0] if kaynak else None, 'hatalar': hatalar}
    gereken = [t for t in tum if _g13_tarih(t) >= bugun]
    blok['gecmis'] = [t for t in tum if _g13_tarih(t) < bugun][-3:]
    if gereken:
        s = sonraki_ppk(gereken, bugun)
        blok['sonraki'] = s
        blok['gelecek'] = gereken[:4]
        blok['durum'] = 'ok'
        # gelecek yıl sayfası okunamadıysa uyarı (tarih uydurulmaz)
        gy_ok = any(str(bugun.year + 1) in (k or '') for k in kaynak)
        if not gy_ok:
            blok['uyari'] = f'{bugun.year + 1} takvimi alınamadı — liste {bugun.year} sonuyla sınırlı'
    else:
        blok['durum'] = 'veri yok'
        blok['not'] = 'TCMB sayfasında bugünden sonraki PPK tarihi bulunamadı'
    return blok


def evds_anahtar_var() -> bool:
    return bool(os.environ.get('EVDS_KEY', '').strip())


def makro_risk_blogu(getiri_json: dict | None = None, faiz: dict | None = None,
                     tufe: dict | None = None, cd_verisi=None) -> dict:
    """Saf fonksiyon: TR risk kartı bloğu (rezerv/CDS hariç — ağ tarafı `tr_risk_blogu`).

    Kural: değer yoksa alan None + 'veri yok' açıklaması; uydurma sayı yok.
    """
    blok = {'uretildi': utc_now_iso()}
    if getiri_json is None:
        try:
            getiri_json = json.loads((DATA_DIR / 'getiri.json').read_text(encoding='utf-8'))
        except Exception:
            getiri_json = {}
    tahvil = tahvil_getirileri(getiri_json)
    if tahvil.get('2Y') is None and tahvil.get('10Y') is None:
        tahvil['goster'] = 'tahvil_durum'
        tahvil['tahvil_durum'] = (getiri_json or {}).get('tahvil_durum') or 'veri yok'
        tahvil['metin'] = f'Tahvil getirisi yok — kaynak durumu: {tahvil["tahvil_durum"]}'
    blok['tahvil'] = tahvil

    faiz = faiz if faiz is not None else ((tufe or {}).get('_faiz') or {})
    pol = _g13_sayi((faiz or {}).get('faiz'))
    tufe_y = _g13_sayi((tufe or {}).get('yillik'))
    blok['politika'] = {'faiz': pol, 'uygulama': (faiz or {}).get('tarih'),
                        'karar': (faiz or {}).get('karar_tarihi'),
                        'durum': 'ok' if pol is not None else 'veri yok'}
    blok['tufe'] = {'yillik': tufe_y, 'tarih': (tufe or {}).get('tarih'),
                    'durum': 'ok' if tufe_y is not None else 'veri yok'}
    rf = reel_faiz(pol, tufe_y)
    blok['reel_faiz'] = {'deger': rf, 'formul': 'politika faizi − yıllık TÜFE',
                         'durum': 'ok' if rf is not None else 'veri yok'}
    blok['reel_faiz']['yorum'] = (None if rf is None else
                                  ('POZİTİF reel faiz → TL mevduat cazip, altın/dövize baskı'
                                   if rf > 0 else
                                   'NEGATİF reel faiz → altın/döviz talebi güçlü'))

    # TCMB rezervleri — EVDS anahtarı şart (secret adı: EVDS_KEY)
    blok['rezerv'] = {'durum': 'anahtar yok' if not evds_anahtar_var() else 'anahtar var',
                      'secret': 'EVDS_KEY',
                      'metin': ('anahtar yok — TCMB rezervleri için GitHub Secrets\'a EVDS_KEY eklenmeli'
                                if not evds_anahtar_var()
                                else 'anahtar var — rezerv serisi bu sürümde çekilmiyor (EVDS seri kodu bekleniyor)')}
    # 5Y CDS — anahtarsız güvenilir kaynak yok → EKLENMEDİ
    blok['cds'] = {'durum': 'eklenmedi',
                   'metin': '5Y CDS: anahtarsız güvenilir kaynak bulunamadı — bilinçli olarak eklenmedi'}
    blok['cds'].update(cd_verisi or {})
    return blok


def tr_risk_blogu(getiri_json=None, faiz=None, tufe=None) -> dict:
    """Ağ: TR risk kartı = makro_risk_blogu + PPK takvimi (TCMB parse)."""
    blok = makro_risk_blogu(getiri_json, faiz, tufe)
    try:
        blok['ppk'] = ppk_takvimi()
    except Exception as e:
        blok['ppk'] = {'durum': 'veri yok', 'hata': str(e)[:80]}
    return blok


def reel_bist_verisi(endeks: dict | None) -> dict:
    """Ağ: XU100 (G09 tam serisi) + USDTRY + gram altın 1 yıllık seriler → reel BIST bloğu.

    XU100 serisi G09'daki `endeks['seri']` (yeniden indirilmez). Kur: yfinance USDTRY=X,
    gram altın: ons (GC=F) / 31,1034768 × USDTRY — panel manşet gram yöntemiyle aynı.
    Kaynak düşerse ilgili bacak 'veri yok'; uydurma değer yok.
    """
    blok = {'durum': 'veri yok', 'kaynak': {}}
    xu = [(_g13_tarih(t), v) for t, v in ((endeks or {}).get('seri') or [])]
    if not xu:
        blok['not'] = 'XU100 serisi (G09) yok — reel BIST hesaplanamadı'
        return blok
    blok['kaynak']['xu100'] = 'yfinance XU100.IS (G09 tam seri)'
    kur, ons = [], []
    try:
        import yfinance as yf
        import warnings
        warnings.filterwarnings('ignore')
        h = yf.Ticker('USDTRY=X').history(period='1y', interval='1d').dropna()
        kur = [(_g13_tarih(ix), float(v)) for ix, v in h['Close'].items()]
        blok['kaynak']['usdtry'] = 'yfinance USDTRY=X'
    except Exception as e:
        log(f"G13 USDTRY hata: {str(e)[:50]}")
        blok['kur_hata'] = str(e)[:80]
    try:
        import yfinance as yf
        import warnings
        warnings.filterwarnings('ignore')
        g = yf.Ticker('GC=F').history(period='1y', interval='1d').dropna()
        ons = [(_g13_tarih(ix), float(v)) for ix, v in g['Close'].items()]
        blok['kaynak']['ons'] = 'yfinance GC=F'
    except Exception as e:
        log(f"G13 ons hata: {str(e)[:50]}")
        blok['ons_hata'] = str(e)[:80]
    if not kur or not ons:
        blok['not'] = 'USDTRY veya ons altın serisi alınamadı — USD/altın bazlı getiri hesaplanamadı'
        if kur:
            blok['kur_seri'] = [[t.isoformat(), round(v, 4)] for t, v in kur]
        return blok
    hizali = seri_eslestir(xu, kur, ons)
    gram = [(t, vals[1] / ONS_GRAM_G13 * vals[2]) for t, vals in hizali]
    seriler = reel_bist_serileri(xu, kur, gram)
    if seriler.get('durum') != 'ok':
        blok['not'] = 'seriler hizalanamadı (ortak gün yok)'
        return blok
    blok.update(seriler)
    blok['getiriler'] = reel_bist_getirileri(seriler)
    blok['kaynak']['gram_altin'] = 'ons(GC=F) / 31,1034768 × USDTRY'
    return blok


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


def golge_gostergeler(df, endeks: dict | None) -> dict:
    """G09 — gölge mod göstergeleri. SADECE hesaplama/log/UI içindir.

    skor ve sinyal hesabına DAHİL EDİLMEZ. Ağa çıkmaz (saf fonksiyon).
    df: HGDG_TARIH + HGDG_KAPANIS/HGDG_HACIM/HGDG_MIN/HGDG_MAX kolonlu DataFrame
        (tarih sıralı, ham veri — tüm indikatörler henüz hesaplanmamış olabilir).
    Hesaplanamayan alan None döner (uydurma yok).
    """
    from indikatorler import rs_degisim, hacim_orani, vol20, zirve_uzak, trend_atr, sma, atr
    import pandas as pd

    g = {'RS20': None, 'RS60': None, 'HACIM_ORAN': None, 'VOL20': None,
         'ZIRVE_UZAK': None, 'TREND_ATR': None}
    try:
        kapanis = df['HGDG_KAPANIS'].astype(float).reset_index(drop=True)
        hacim = df['HGDG_HACIM'].astype(float).reset_index(drop=True)
        tarihler = pd.to_datetime(df['HGDG_TARIH']).dt.strftime('%Y-%m-%d').reset_index(drop=True)
        g['HACIM_ORAN'] = hacim_orani(hacim)
        g['VOL20'] = vol20(kapanis)
        g['ZIRVE_UZAK'] = zirve_uzak(kapanis)
        g['TREND_ATR'] = trend_atr(kapanis, sma(kapanis, 50), atr(df['HGDG_MAX'].astype(float),
                                                                 df['HGDG_MIN'].astype(float), kapanis))
        # RS20/RS60 — endeks tam serisi varsa tarih bazlı hizala
        seri = (endeks or {}).get('seri') or []
        if seri:
            end_s = pd.Series({str(t)[:10]: float(v) for t, v in seri}, dtype=float)
            hisse_s = pd.Series(kapanis.values, index=tarihler.values, dtype=float)
            hisse_s = hisse_s[~hisse_s.index.duplicated(keep='last')].sort_index()
            ortak = hisse_s.index.intersection(end_s.index)
            if len(ortak) >= 21:
                h, e = hisse_s.loc[ortak], end_s.loc[ortak]
                g['RS20'] = rs_degisim(h, e, 20)
                g['RS60'] = rs_degisim(h, e, 60)
    except Exception:
        return g
    return g


def sinyalleri_hesapla(hisse_veri: dict, ipo: dict | None = None, endeks: dict | None = None) -> dict:
    """OHLCV verisinden indikatör + sinyal hesapla (indikatorler.py mantığı).

    G05 filtreleri (saf, ağsız):
      - durum        : 'gecici' / 'kesin' — bar tarihi bugünden eskiyse kesin,
                       bugünse TR 18:30 sonrası kesin
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

    ipo = ipo or {}
    durum = 'gecici'      # döngü hiç dönmezse (boş veri) güvenli varsayılan
    sonuclar = []
    for sembol, rows in hisse_veri.items():
        durum = 'gecici'
        if len(rows) < 60:
            continue
        # Kesinlik, hissenin SON BAR tarihine göre (dünün barı → kesin)
        try:
            durum = sinyal_durumu(rows[-1].get('tarih') if rows else None)
        except Exception:
            durum = 'gecici'
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
                # ── G09 gölge mod (skor/sinyal hesabına GİRMEZ) ──
                **golge_gostergeler(df, endeks),
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
    # G05 — üst düzey durum: hisselerin çoğunluğu kesinse 'kesin'
    kesin_say = sum(1 for r in sonuclar if r.get('durum') == 'kesin')
    durum = 'kesin' if sonuclar and kesin_say * 2 >= len(sonuclar) else 'gecici'
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


def test_senaryolari(hisse_veri: dict, endeks_serisi=None) -> dict:
    """TEST SENARYOLARI — 'geçmişte sinyal olsaydı şu an ne olurdu?' hesabı.

    G08 — gerçek veri + gerçek sinyal geçmişi (uydurma yok):
    - Giriş: kesin sinyalin ERTESİ günü açılış (kilitli günde ilk kilitsiz güne kayar, G05)
    - Çıkış: 5/10/20 iş günü vade VEYA 2×ATR stop / 3×ATR hedef — hangisi önce
      (gün içi max/min ile; aynı gün stop+hedef → stop; taban kilidinde ilk kilitsiz güne kayar)
    - Maliyet: MALIYET (gidiş-dönüş %0,2) net getiriden düşülür
    - Alfa: işlem getirisi − XU100 getirisi (aynı giriş/çıkış tarihleri)
    - Sermaye: kronolojik 100.000 TL / max 10 pozisyon, nakit yoksa sinyal atlanır
    Eski alanlar (pazartesi_acilis, ertesi_gun_acilis, stop_losslu, ...) bir sürüm boyunca korunur.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from indikatorler import tum_indikatorler, sinyal_hesapla
    import pandas as pd

    # G08 — giriş sadece kesin sinyalin ertesi günü açılışta; son bar için ertesi gün yok.
    # Skor istatistiğinden hariç evren: yeni halka arz + RISKLI (G05 md.4/md.6).
    veri_yok = {'durum': 'veri yok', 'aciklama': 'Hisse verisi alınamadı.'}
    if not hisse_veri:
        return veri_yok

    # 1. Aşama — her hisse için bar tablosu + sinyal serisi (ağ YOK)
    tablolar = {}          # sembol → ind (DataFrame, tüm indikatörler)
    sinyal_serisi = {}     # sembol → [(i, sinyal_dict, kilitler_dict)]
    haric = {}             # sembol → hariç tutulma nedeni (G08: RİSKLİ / İZLE)
    for sembol, rows in hisse_veri.items():
        if len(rows) < 60:
            continue
        uygun, neden, _ = uygun_evren(rows)
        if not uygun:                       # yeni halka arz → istatistik dışı
            haric[sembol] = neden
            continue
        # G08 md.7 — RİSKLİ ve İZLE etiketli hisseler backtest'e girmez.
        # Etiket `riskli_tespit` + likidite eşiği ile yeniden üretilir (saf, ağsız).
        risk = riskli_tespit(rows)
        if risk:
            haric[sembol] = f'RİSKLİ ({risk})'
            continue
        lik = likidite_tl(rows)
        if lik is not None and lik < LIKIDITE_ESIK_TL:
            haric[sembol] = 'İZLE (likidite eşiği altı)'
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
        # G05 — kilitli günler (tavan/taban): o gün ne giriş ne çıkış yapılabilir
        kilitler = {}
        for k in range(1, len(ind)):
            kk = kilit_tespit({'kapanis': ind.iloc[k]['HGDG_KAPANIS'], 'max': ind.iloc[k]['HGDG_MAX'],
                               'min': ind.iloc[k]['HGDG_MIN']}, ind.iloc[k - 1]['HGDG_KAPANIS'])
            if kk:
                kilitler[k] = kk
        seri = []
        for i in range(60, len(ind) - 1):
            s = sinyal_hesapla(ind.iloc[i])
            if s['sinyal'] in ('AL', 'DİKKAT_AL'):
                # RISKLI hisse (son 10 barda ≥3 taban) backtest'e girmez — o bar tarihinde
                son_rows = rows[:i + 1]
                if riskli_tespit(son_rows):
                    continue
                seri.append((i, s))
        if seri:
            tablolar[sembol] = ind
            sinyal_serisi[sembol] = (seri, kilitler, rows)

    # 2. Aşama — pozisyon çakışmasını sembol bazında çöz (tarih sırasıyla)
    #    Aynı hissede açık pozisyon varken yeni giriş yok.
    tum_islemler = []
    serbest = {}           # sembol → son çıkış bar tarihi (yeni sinyal bu tarihten SONRA olmalı)
    adaylar = []
    for sembol, (seri, kilitler, rows) in sinyal_serisi.items():
        for i, s in seri:
            adaylar.append((pd.Timestamp(tablolar[sembol].iloc[i]['HGDG_TARIH']), sembol, i, s, kilitler, rows))
    adaylar.sort(key=lambda x: (x[0], x[1]))
    for _t, sembol, i, s, kilitler, rows in adaylar:
        if sembol in serbest and i <= serbest[sembol]:
            continue                                   # pozisyon açıkken gelen sinyal → atlanır
        islem = _islem_hesapla(sembol, i, s, tablolar[sembol], kilitler)
        if not islem:
            continue
        tum_islemler.append(islem)
        serbest[sembol] = islem['_cikis_i']
    for x in tum_islemler:
        x.pop('_cikis_i', None)

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
    for islem in tum_islemler:
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

    # 2.4 — Sermaye simülasyonu — G08: KRONOLOJİK (100K TL, max 10 pozisyon, nakit yoksa atla).
    # Eski sürüm ilk 10 işlemi sembol sırasıyla seçiyordu (seçim yanlılığı) — o davranış kaldırıldı,
    # dönen alan adları (sonuc/kar_zarar/islem/tahsis/strateji) geriye uyumluluk için korundu.
    def sermaye(islemler, stop_mu=False, baslangic=None, tahsis=None):
        baslangic = BT_SERMAYE if baslangic is None else baslangic
        tahsis = (baslangic / BT_MAX_POZISYON) if tahsis is None else tahsis
        sim = sermaye_simule(islemler, baslangic=baslangic, max_pozisyon=BT_MAX_POZISYON)
        return {'baslangic': baslangic, 'sonuc': sim['sonuc'], 'kar_zarar': sim['kar_zarar'],
                'islem': sim['islem'], 'atlanan': sim['atlanan'], 'tahsis': round(tahsis, 0),
                'gerceklesen_max_dd_yuzde': sim['gerceklesen_max_dd_yuzde'],
                'max_drawdown_yuzde': sim['max_drawdown_yuzde'],   # geriye uyum
                'beklenen_kar': sim['beklenen_kar'],
                'mutabakat_fark': sim['mutabakat_fark'],
                'mutabakat_fark_yuzde': sim['mutabakat_fark_yuzde'],
                'strateji': 'kronolojik'}

    # 2.5 — G08: Benchmark (XU100) alfa + metrikler + skor seviyesi tabloları.
    #      `endeks_serisi`: [(tarih_str, kapanis)] artan sıralı (G09 tam serisi).
    #      Endeks yoksa alfa alanları None döner (uydurma yok).
    endeks_serisi = sorted(endeks_serisi or [], key=lambda x: str(x[0])[:10])

    def _endeks_getiri(tarih_a: str, tarih_b: str):
        """tarih_a kapanışından tarih_b kapanışına XU100 getirisi (%)."""
        if not endeks_serisi:
            return None
        a = b = None
        for t, k in endeks_serisi:
            try:
                kf = float(k)
            except (TypeError, ValueError):
                continue
            ts = str(t)[:10]
            if ts <= tarih_a:
                a = kf
            if ts <= tarih_b:
                b = kf
        if not a or not b or a <= 0:
            return None
        return round((b / a - 1) * 100, 1)

    for x in tum_islemler:
        bm = _endeks_getiri(x['giris_tarih'], x['cikis_tarih'])
        x['xu100_getiri_yuzde'] = bm
        x['alfa_yuzde'] = round(x['getiri_yuzde'] - bm, 1) if bm is not None else None

    def alfa_grup(islemler):
        al = [x['alfa_yuzde'] for x in islemler if x.get('alfa_yuzde') is not None]
        return round(sum(al) / len(al), 1) if al else None

    def metrikler(islemler):
        g = [x['getiri_yuzde'] for x in islemler]
        if not g:
            return {'islem': 0, 'isabet': None, 'ortalama': None, 'ortalama_alfa': None,
                    'profit_factor': None, 'max_drawdown': None, 'devir': None}
        kaz = sum(y for y in g if y > 0)
        kay = -sum(y for y in g if y < 0)
        sim = sermaye_simule(islemler)
        ort_gun = sum(x.get('vade_gun') or 1 for x in islemler) / len(islemler)
        return {
            'islem': len(g),
            'isabet': round(sum(1 for y in g if y > 0) / len(g), 3),
            'ortalama': round(sum(g) / len(g), 2),
            'ortalama_alfa': alfa_grup(islemler),
            # kâr/zarar 0 ise oran tanımsız → None (sonsuz yazılmaz)
            'profit_factor': round(kaz / kay, 2) if kay > 0 else None,
            'max_drawdown': sim['gerceklesen_max_dd_yuzde'],
            # devir: yıllık ortalama işlem sayısı (252 / ortalama vade)
            'devir': round(252 / ort_gun, 1) if ort_gun > 0 else None,
        }

    # Skor seviyesine göre ayrı tablo: 2, 3, ≥4
    skor_tablosu = []
    for etiket, kosul in (('2', lambda k: k == 2), ('3', lambda k: k == 3), ('≥4', lambda k: k >= 4)):
        grup = [x for x in tum_islemler if kosul(x['skor'])]
        m = metrikler(grup)
        m['skor'] = etiket
        skor_tablosu.append(m)

    # G08 — eski senaryo adları korunur (bir sürüm), kaynak artık tek işlem listesi.
    # 'pazartesi_acilis': sinyal tarihi pazartesi olan işlemler (eski S1 tanımına en yakın kesit).
    # 'stop_losslu': eski %5 sabit stop → yeni ATR stop sonuçlarını taşır; alan adı korunur.
    pazartesi_islemleri = [x for x in tum_islemler if _hafta_gunu(x['sinyal_tarih']) == 0]
    gunluk_islemler = tum_islemler
    stop_islemleri = [x for x in tum_islemler if x['cikis_neden'] == 'stop']

    return {
        'pazartesi_acilis': ozetle(pazartesi_islemleri, 'Pazartesi sinyalleri (yeni kurallar)'),
        'ertesi_gun_acilis': ozetle(gunluk_islemler, 'Sinyal ertesi gün açılışında al'),
        'stop_losslu': ozetle(stop_islemleri, "ATR stop ile kapanan işlemler", stop_mu=True),
        'hisse_bazli': hisse_ozet[:20],
        'sermaye': {
            'pazartesi': sermaye(pazartesi_islemleri),
            'ertesi': sermaye(gunluk_islemler),
            'stop': sermaye(stop_islemleri),
        },
        # G08 — yeni (XU100'e göre) alanlar; eski alanlar bir sürüm boyunca korunur
        'metrik': metrikler(tum_islemler),
        'skor_tablosu': skor_tablosu,
        'benchmark': 'XU100',
        'parametre': {'maliyet': MALIYET, 'vade_gun': list(BT_VADE_GUN),
                      'atr_stop': BT_ATR_STOP, 'atr_hedef': BT_ATR_HEDEF,
                      'sermaye': BT_SERMAYE, 'max_pozisyon': BT_MAX_POZISYON,
                      'benchmark': 'XU100'},
        # G08 md.7 — backtest evreninden çıkarılan hisseler (RİSKLİ / İZLE / yeni halka arz)
        'haric': {'adet': len(haric), 'hisseler': dict(sorted(haric.items()))},
        'aciklama': ('Senaryolar GERÇEK veriyle hesaplanır: sinyal günü kapanışında AL/DİKKAT_AL üreten '
                     'hisse, ertesi gün açılıştan alınır. Çıkış 5/10/20 iş günü vade veya 2×ATR stop / '
                     '3×ATR hedef — hangisi önce. Alfa = işlem getirisi − XU100 getirisi (aynı tarihler).'),
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
    # G05 — karneye SADECE kesin sinyaller yazılır (bar bugünden eski ya da TR 18:30 sonrası).
    # Geçici sinyaller karnede yer almaz: gün içi anlık görüntü kesin sonuç değil.
    if sinyaller.get('durum') != 'kesin':
        log(f"Sinyal geçmişi: durum={sinyaller.get('durum')} → karneye yazılmadı")
        try:
            return json.loads(GECMIS.read_text())
        except Exception:
            return {}
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
               'squeeze', 'ay_oncesi', 'stop', 'hedef',
               # G09 — gölge mod göstergeleri (denetim IC'si için kaydedilir)
               'RS20', 'RS60', 'HACIM_ORAN', 'VOL20', 'ZIRVE_UZAK', 'TREND_ATR')
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


def hisse_verisi_cek(liste: list) -> tuple:
    """Hisse OHLCV — 3 kademeli failover (patron önerisi):
    1) İş Yatırım (TR IP — en hızlı, gerçek zamanlı)
    2) borsapy TradingView provider (İş Yatırım'dan bağımsız, global)
    3) yfinance (garanti fallback)

    G08: `main()` ve `backtest_gercek_veri()` aynı zinciri kullanır.
    Eksik-hisse düzeltmesi: kademe 2 sonrası tek tek düşen hisseler için
    hisse bazlı yfinance (.IS) tamamlaması (`tamamla_yfinance`) yapılır;
    hiç gelemeyenler `eksik` listesinde nedeniyle birlikte döner.
    Returns: (hisse_veri, kaynak_adı, eksik_hisseler, eksik_nedenler)
    """
    nedenler = {}
    hisse_veri = cek_isyatirim(liste)
    kaynak = "isyatirim"
    if not hisse_veri:
        log("İş Yatırım başarısız → borsapy (TradingView) deneniyor")
        hisse_veri = cek_borsapy(liste, nedenler=nedenler)
        kaynak = "borsapy-tv"
    if not hisse_veri:
        log("borsapy başarısız → yfinance deneniyor")
        hisse_veri = cek_yfinance(liste)
        kaynak = "yfinance"
        nedenler = {}
    if not hisse_veri:
        log("KRİTİK: TÜM KAYNAKLAR BAŞARISIZ")
        return {}, kaynak, list(liste), {s: 'tüm kaynaklar başarısız' for s in liste}

    eksik = [s for s in liste if s not in hisse_veri]
    if eksik and kaynak != "yfinance":
        # Kısmi eksik → hisse bazlı yfinance (.IS) tamamlaması
        log(f"{len(eksik)} hisse eksik → hisse bazlı yfinance tamamlaması: {', '.join(eksik)}")
        eklenen, hala_yok = tamamla_yfinance(hisse_veri, eksik, nedenler=nedenler)
        if eklenen:
            log(f"yfinance tamamladı: {', '.join(eklenen)} ({len(eklenen)} hisse)")
        eksik = hala_yok
        if eklenen:
            kaynak = f"{kaynak}+yfinance"

    eksik_nedenler = {s: nedenler.get(s, 'bilinmiyor') for s in eksik}
    if eksik:
        log(f"EKSİK {len(eksik)} hisse: " +
            "; ".join(f"{s}={eksik_nedenler[s]}" for s in eksik))
    return hisse_veri, kaynak, eksik, eksik_nedenler


def backtest_gercek_veri(liste: list | None = None, endeks: dict | None = None) -> dict:
    """G08 — Backtest'i GERÇEK geçmiş veriyle yeniden çalıştırır.

    `main()` ile aynı veri zinciri (hisse_verisi_cek failover + bölünme düzeltmesi +
    XU100 tam serisi). Dönen sözlük `test_senaryolari` çıktısıdır; ek olarak
    'veri' bölümünde kaynak/bar/tarih aralığı bilgisi bulunur. Ağ erişimi gerekir;
    testler bu fonksiyonu çağırmaz (saf fonksiyonlar test edilir).
    """
    if liste is None:
        liste = bist100_listesi()
    log(f"G08 backtest: {len(liste)} hisse çekiliyor")
    hisse_veri, kaynak, eksik, eksik_nedenler = hisse_verisi_cek(liste)
    if not hisse_veri:
        return {'durum': 'veri yok', 'aciklama': 'Hisse verisi alınamadı.'}
    try:
        bolunme_uygula(hisse_veri)          # analizden ÖNCE (RALYH −%98 vakası)
    except Exception as e:
        log(f"bölünme düzeltmesi hata: {str(e)[:60]}")
    if endeks is None:
        endeks = endeks_verisi() or {}
    senaryolar = test_senaryolari(hisse_veri, endeks.get('seri') or [])
    araliklar = [(str(rows[0].get('tarih'))[:10], str(rows[-1].get('tarih'))[:10])
                 for rows in hisse_veri.values() if rows]
    senaryolar['veri'] = {
        'kaynak': kaynak,
        'hisse': len(hisse_veri),
        'eksik_hisseler': eksik,
        'eksik_nedenler': eksik_nedenler,
        'bar': sum(len(r) for r in hisse_veri.values()),
        'baslangic': min((a for a, _ in araliklar), default=None),
        'bitis': max((b for _, b in araliklar), default=None),
        'endeks_bar': len((endeks or {}).get('seri') or []),
        'endeks_tarih': (endeks or {}).get('tarih'),
    }
    return senaryolar


def main():
    log("=== BIST PANEL veri çekme başladı ===")
    liste = bist100_listesi()
    log(f"BIST 100 listesi: {len(liste)} hisse")

    # 1. Hisse verisi — 3 kademeli failover
    hisse_veri, kaynak, eksik_hisseler, eksik_nedenler = hisse_verisi_cek(liste)
    if eksik_hisseler:
        log(f"UYARI: {len(eksik_hisseler)} hisse alınamadı → "
            + ", ".join(f"{s}={eksik_nedenler.get(s, '?')}" for s in eksik_hisseler))

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
    saglik = veri_saglik_kontrolu(hisse_veri or {}, endeks, kaynak,
                                  eksik_hisseler=eksik_hisseler,
                                  eksik_nedenler=eksik_nedenler)
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

    # 3b. G13 — reel BIST (XU100 / USDTRY, XU100 / gram altın) + TR risk kartı
    try:
        reel_bist = reel_bist_verisi(endeks)
    except Exception as e:
        log(f"G13 reel bist hata: {str(e)[:60]}")
        reel_bist = {'durum': 'veri yok', 'hata': str(e)[:80]}
    try:
        tr_risk = tr_risk_blogu(faiz=faiz, tufe=tufe)
    except Exception as e:
        log(f"G13 tr risk hata: {str(e)[:60]}")
        tr_risk = {'durum': 'veri yok', 'hata': str(e)[:80]}
    log(f"G13: reel_bist={reel_bist.get('durum')} | tr_risk reel_faiz="
        f"{(tr_risk.get('reel_faiz') or {}).get('deger')} | ppk="
        f"{((tr_risk.get('ppk') or {}).get('sonraki') or {}).get('tarih')}")

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
    sinyaller = sinyalleri_hesapla(hisse_veri, ipo, endeks) if hisse_veri else {'al': [], 'tut': [], 'sat': [], 'izle': [], 'riskli': [], 'toplam': 0, 'hesap_tarihi': ''}

    # 5. Test senaryoları — G08: XU100 tam serisi (G09) alfa hesabı için verilir
    endeks_serisi = (endeks or {}).get('seri') or []
    senaryolar = test_senaryolari(hisse_veri, endeks_serisi) if hisse_veri else {}

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

    # 5h2. G09 — piyasa genişliği (100 hissenin TAMAMINDAN, gölge mod)
    # Bağımsız try/except: düşerse diğer bloklar yazılmaya devam eder.
    genislik = {'durum': 'veri yok'}
    if hisse_veri:
        try:
            from indikatorler import genislik_hesapla
            import pandas as _pd
            seriler = {}
            for _s, _rows in hisse_veri.items():
                if not _rows:
                    continue
                _df = _pd.DataFrame(_rows).sort_values('tarih')
                seriler[_s] = _pd.DataFrame({'HGDG_KAPANIS': _df['kapanis'].astype(float)})
            genislik = genislik_hesapla(seriler)
            genislik['tarih'] = endeks.get('tarih') if endeks else None
            log(f"G09 genişlik: MA50 üstü %{genislik.get('ma50_ustu_yuzde')} · "
                f"yükselen {genislik.get('yukselen')} / düşen {genislik.get('dusen')} · "
                f"52h zirve {genislik.get('yeni_zirve_52h')} / dip {genislik.get('yeni_dip_52h')} "
                f"({genislik.get('hisse')} hisse)")
        except Exception as e:
            log(f"G09 genişlik hata: {str(e)[:60]}")
            genislik = {'durum': 'veri yok'}

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
        'reel_bist': reel_bist,
        'tr_risk': tr_risk,
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
        'genislik': genislik,
    }
    (DATA_DIR / 'piyasa.json').write_text(json.dumps(paket, ensure_ascii=False, indent=1), encoding='utf-8')
    log(f"piyasa.json yazıldı: {os.path.getsize(DATA_DIR / 'piyasa.json')} byte")
    log("=== TAMAM ===")


if __name__ == '__main__':
    main()
