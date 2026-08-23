#!/usr/bin/env python3
"""Teknik indikatör modülü — RSI, MACD, SMA/EMA, Bollinger, MFI (para akışı), OBV, Stoch RSI, ATR."""
import numpy as np
import pandas as pd

def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()

def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(100)

def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    mid = sma(close, n)
    std = close.rolling(n).std()
    upper = mid + k * std
    lower = mid - k * std
    return mid, upper, lower

def bbw(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.Series:
    """Bollinger Band Width — bant genişliği (squeeze tespiti için).
    Daralan bant = düşen volatilite = potansiyel kırılım öncesi sıkışma."""
    mid, upper, lower = bollinger(close, n, k)
    width = (upper - lower) / mid.replace(0, np.nan)
    return width * 100  # yüzde

def squeeze_tespit(close: pd.Series, donem: int = 60, esik_yuzde: float = 25.0) -> pd.Series:
    """Bollinger Squeeze: BBW son `donem` barda (varsayılan 60) en dar %25'lik dilimdeyse.
    Dönüş: 'SQUEEZE' (sıkışma), 'KIRILIM_YUKARI'/'KIRILIM_ASAGI' (bant genişliyor + fiyat yönü),
    'NORMAL' (geniş bant, hareketli piyasa)."""
    w = bbw(close)
    durum = pd.Series('NORMAL', index=close.index)
    for i in range(donem, len(w)):
        pencere = w.iloc[i - donem:i].dropna()
        if len(pencere) < donem // 2 or pencere.std() == 0:
            continue
        # Mevcut genişlik, son `donem` barda yüzde kaçıncı dilimde?
        yuzdelik = (w.iloc[i] - pencere.min()) / (pencere.max() - pencere.min()) * 100
        if yuzdelik < esik_yuzde:
            durum.iloc[i] = 'SQUEEZE'
        else:
            # Squeeze'den çıkış: genişleme + fiyat yönü
            onceki = durum.iloc[i - 1]
            if onceki == 'SQUEEZE' and w.iloc[i] > w.iloc[i - 1]:
                durum.iloc[i] = 'KIRILIM_YUKARI' if close.iloc[i] > close.iloc[i - 1] else 'KIRILIM_ASAGI'
    return durum

def mfi(high, low, close, volume, n: int = 14) -> pd.Series:
    """Money Flow Index — para giriş/çıkışı osilatörü."""
    tp = (high + low + close) / 3
    mf = tp * volume
    pos = pd.Series(0.0, index=tp.index)
    neg = pd.Series(0.0, index=tp.index)
    diff = tp.diff()
    pos[diff > 0] = mf[diff > 0]
    neg[diff < 0] = mf[diff < 0]
    pos_sum = pos.rolling(n).sum()
    neg_sum = neg.rolling(n).sum()
    mfi = 100 - (100 / (1 + pos_sum / neg_sum.replace(0, np.nan)))
    return mfi.fillna(50)

def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume — hacim bazlı para akışı."""
    sign = np.sign(close.diff().fillna(0))
    return (sign * volume).cumsum()

def stoch_rsi(close: pd.Series, n: int = 14, k: int = 3, d: int = 3):
    rsi_v = rsi(close, n)
    rsi_min = rsi_v.rolling(n).min()
    rsi_max = rsi_v.rolling(n).max()
    stoch = (rsi_v - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)
    k_line = stoch.rolling(k).mean() * 100
    d_line = k_line.rolling(d).mean()
    return k_line, d_line

def pivot_seviyeler(high, low, close):
    """Klasik günlük pivot seviyeleri — önceki barın H/L/C'sinden hesaplanır.
    P = (H+L+C)/3, R1/R2 = direnç (üst), S1/S2 = destek (alt).
    Yatırımcıların emirlerini koyduğu PSİKOLOJİK seviyeler:
    - S1 (1. Destek): fiyat düşerken ilk tutunma noktası
    - S2 (2. Destek): daha derin düşüşte ikinci tutunma noktası
    - R1 (1. Direnç): fiyat yükselirken ilk satış/kar bölgesi
    - R2 (2. Direnç): daha güçlü yükselişte ikinci satış bölgesi
    Dönüş: {'pivot': P, 'r1': R1, 'r2': R2, 's1': S1, 's2': S2} (float, NaN olabilir)"""
    H = float(high.iloc[-1]) if hasattr(high, 'iloc') else float(high[-1])
    L = float(low.iloc[-1]) if hasattr(low, 'iloc') else float(low[-1])
    C = float(close.iloc[-1]) if hasattr(close, 'iloc') else float(close[-1])
    P = (H + L + C) / 3
    return {
        'pivot': round(P, 2),
        'r1': round(2 * P - L, 2),
        's1': round(2 * P - H, 2),
        'r2': round(P + (H - L), 2),
        's2': round(P - (H - L), 2),
    }

def swing_seviyeler(low, high, donem: int = 20):
    """Yatay destek/direnç: son `donem` barın en düşük ve en yüksek değeri.
    Bu seviyeler kırılırsa trend değişimi sinyali sayılır."""
    L = float(low.iloc[-donem:].min()) if hasattr(low, 'iloc') else float(min(low[-donem:]))
    H = float(high.iloc[-donem:].max()) if hasattr(high, 'iloc') else float(max(high[-donem:]))
    return {'destek': round(L, 2), 'direnc': round(H, 2), 'donem': donem}

def seviye_durumu(fiyat: float, s: dict) -> str:
    """Fiyatın pivot seviyelerine göre konumu — insan okunur etiket."""
    if fiyat > s['r1']:
        return f"fiyat 1. Direnç (R1) {s['r1']:.2f} TL'nin ÜZERİNDE → üstte hedef: 2. Direnç (R2) {s['r2']:.2f} TL"
    if fiyat < s['s1']:
        return f"fiyat 1. Destek (S1) {s['s1']:.2f} TL'nin ALTINDA → aşağıda tutunma: 2. Destek (S2) {s['s2']:.2f} TL"
    if fiyat > s['pivot']:
        return f"fiyat pivot ({s['pivot']:.2f} TL) üzerinde, 1. Direnç (R1) {s['r1']:.2f} TL'ye marj var"
    return f"fiyat pivot ({s['pivot']:.2f} TL) altında, 1. Destek (S1) {s['s1']:.2f} TL'ye marj var"

def ict_sinyalleri(h: pd.DataFrame, donem: int = 20) -> dict:
    """ICT sinyalleri (son bar) — likidite süpürmesi + Fair Value Gap + momentum kırılımı.

    Kaynak: borsaci/quant_alpha.py (saidsurucu) — gerçek veriyle test edildi.
    Skora dokunmaz, SADECE açıklama katmanı üretir (anti-hallüsinasyon: hesaplanan değerler).

    - BULLISH_LIQUIDITY_SWEEP: destek (son N barın en düşüğü) kırıldı ama kapanış üstüne geldi
      → stoplar süpürüldü, alıcı kontrolü ele aldı (tuzak aşağı)
    - BEARISH_LIQUIDITY_SWEEP: direnç (son N barın en yükseği) kırıldı ama kapanış altına döndü
      → yukarı tuzak, satıcı kontrolü ele aldı
    - BULLISH_FVG: fiyat 2 bar önceki yükseğin üzerinde boşluk bıraktı (kurumsal alım izi)
    - BEARISH_FVG: fiyat 2 bar önceki düşüğün altında boşluk bıraktı (kurumsal satış izi)
    - MOMENTUM_KIRILIM_YUKARI/ASAGI: kapanış son N barın zirvesini/dipini geçti
    """
    if len(h) < donem + 3:
        return {}
    high = h['HGDG_MAX'].values
    low = h['HGDG_MIN'].values
    close = h['HGDG_KAPANIS'].values
    i = len(h) - 1
    prior_high = float(high[i - donem:i].max())
    prior_low = float(low[i - donem:i].min())
    sonuc = {}

    # Momentum kırılımı
    if close[i] > prior_high:
        sonuc['momentum'] = ('MOMENTUM_KIRILIM_YUKARI', f"kapanış son {donem} barın zirvesini ({prior_high:.2f} TL) geçti")
    elif close[i] < prior_low:
        sonuc['momentum'] = ('MOMENTUM_KIRILIM_ASAGI', f"kapanış son {donem} barın dibini ({prior_low:.2f} TL) kırdı")

    # Likidite süpürmesi
    midpoint = (high[i] + low[i]) / 2.0
    if low[i] < prior_low and close[i] > prior_low and close[i] > midpoint:
        sonuc['sweep'] = ('BULLISH_LIQUIDITY_SWEEP',
                          f"destek {prior_low:.2f} TL kırıldı ama kapanış üstüne geldi ({close[i]:.2f} TL) → "
                          f"stoplar süpürüldü, aşağı tuzak — alıcı kontrolü ele aldı")
    elif high[i] > prior_high and close[i] < prior_high and close[i] < midpoint:
        sonuc['sweep'] = ('BEARISH_LIQUIDITY_SWEEP',
                          f"direnç {prior_high:.2f} TL kırıldı ama kapanış altına döndü ({close[i]:.2f} TL) → "
                          f"yukarı tuzak — satıcı kontrolü ele aldı")

    # Fair Value Gap (2 bar öncesine göre boşluk)
    if i >= 2:
        if low[i] > high[i - 2]:
            sonuc['fvg'] = ('BULLISH_FVG', f"fiyat 2 bar önceki yükseğin ({high[i-2]:.2f} TL) üzerinde boşluk bıraktı — kurumsal alım izi")
        elif high[i] < low[i - 2]:
            sonuc['fvg'] = ('BEARISH_FVG', f"fiyat 2 bar önceki düşüğün ({low[i-2]:.2f} TL) altında boşluk bıraktı — kurumsal satış izi")

    return sonuc


def atr(high, low, close, n: int = 14) -> pd.Series:
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()

def tum_indikatorler(df: pd.DataFrame) -> pd.DataFrame:
    """Hisse bazlı tüm indikatörleri hesaplar. df: HGDG_TARIH, HGDG_KAPANIS, HGDG_MAX, HGDG_MIN, HGDG_HACIM"""
    out = df.copy()
    out['RSI14'] = rsi(out['HGDG_KAPANIS'])
    out['MACD'], out['MACD_SINYAL'], out['MACD_HIST'] = macd(out['HGDG_KAPANIS'])
    out['SMA20'] = sma(out['HGDG_KAPANIS'], 20)
    out['SMA50'] = sma(out['HGDG_KAPANIS'], 50)
    out['SMA200'] = sma(out['HGDG_KAPANIS'], 200)
    out['EMA20'] = ema(out['HGDG_KAPANIS'], 20)
    out['BB_MID'], out['BB_UST'], out['BB_ALT'] = bollinger(out['HGDG_KAPANIS'])
    out['MFI14'] = mfi(out['HGDG_MAX'], out['HGDG_MIN'], out['HGDG_KAPANIS'], out['HGDG_HACIM'])
    out['OBV'] = obv(out['HGDG_KAPANIS'], out['HGDG_HACIM'])
    out['STOCH_K'], out['STOCH_D'] = stoch_rsi(out['HGDG_KAPANIS'])
    out['ATR14'] = atr(out['HGDG_MAX'], out['HGDG_MIN'], out['HGDG_KAPANIS'])
    out['BBW'] = bbw(out['HGDG_KAPANIS'])
    out['SQUEEZE'] = squeeze_tespit(out['HGDG_KAPANIS'])
    return out

def sinyal_hesapla(son: pd.Series) -> dict:
    """Son bar için al/sat/tut sinyali — çoklu indikatör konsensüsü."""
    s = {}
    fiyat = son['HGDG_KAPANIS']
    # 1. Trend: Fiyat vs SMA50/SMA200
    s['trend'] = 'YUKARI' if (fiyat > son['SMA50'] and son['SMA50'] > son['SMA200']) else ('ASAĞI' if fiyat < son['SMA50'] else 'YATAY')
    # 2. RSI
    r = son['RSI14']
    s['rsi'] = 'ASIRI_ALIM' if r > 70 else ('ASIRI_SATIM' if r < 30 else 'NÖTR')
    # 3. MACD
    s['macd'] = 'AL' if son['MACD'] > son['MACD_SINYAL'] else 'SAT'
    # 4. Bollinger konumu
    bb = (fiyat - son['BB_ALT']) / (son['BB_UST'] - son['BB_ALT']) if son['BB_UST'] != son['BB_ALT'] else 0.5
    s['bb_konum'] = 'DİRENÇ' if bb > 0.9 else ('DESTEK' if bb < 0.1 else 'ORTA')
    # 5. MFI (para akışı)
    m = son['MFI14']
    s['para_akis'] = 'GİRİŞ' if m > 55 else ('ÇIKIŞ' if m < 45 else 'NÖTR')
    # 6. Stoch RSI
    s['stoch'] = 'AL' if son['STOCH_K'] > son['STOCH_D'] else 'SAT'
    # 7. OBV momentum
    s['obv'] = 'GÜÇLÜ' if son.get('OBV_EGIM', 0) > 0 else 'ZAYIF'
    # Skor
    puan = 0
    if s['trend'] == 'YUKARI': puan += 2
    elif s['trend'] == 'ASAĞI': puan -= 2
    if s['rsi'] == 'ASIRI_ALIM': puan -= 1
    elif s['rsi'] == 'ASIRI_SATIM': puan += 1
    if s['macd'] == 'AL': puan += 1
    else: puan -= 1
    if s['para_akis'] == 'GİRİŞ': puan += 1
    elif s['para_akis'] == 'ÇIKIŞ': puan -= 1
    if s['stoch'] == 'AL': puan += 1
    else: puan -= 1
    if s['bb_konum'] == 'DESTEK': puan += 1
    elif s['bb_konum'] == 'DİRENÇ': puan -= 1
    s['skor'] = puan
    # AL/DİKKAT_AL/DİKKAT_SAT/SAT — skor≥4 tam AL, ≥2 dikkatli AL (6 ayda ≥4 neredeyse hiç tetiklenmiyor)
    if puan >= 4:
        s['sinyal'] = 'AL'
    elif puan >= 2:
        s['sinyal'] = 'DİKKAT_AL'
    elif puan <= -4:
        s['sinyal'] = 'SAT'
    elif puan <= -2:
        s['sinyal'] = 'DİKKAT_SAT'
    else:
        s['sinyal'] = 'TUT'
    # Stop-loss önerisi (ATR bazlı)
    s['stop_loss'] = round(fiyat - 2 * son['ATR14'], 2)
    s['hedef'] = round(fiyat + 3 * son['ATR14'], 2)
    return s
