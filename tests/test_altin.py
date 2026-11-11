"""G03 — altın saf fonksiyon testleri. Ağ bağlantısı gerektirmez."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import altin_cek as A  # noqa: E402


# ── yardımcılar ───────────────────────────────────────────────
def _seri(n=300, taban=4000.0, adim=2.0):
    """Sabit oynaklıkta sentetik OHLC serisi — ATR hesaplanabilsin diye."""
    idx = pd.bdate_range('2024-01-01', periods=n, tz='UTC')
    k = [taban + adim * i for i in range(n)]
    return pd.DataFrame({
        'Open': k,
        'High': [x + 15 for x in k],
        'Low': [x - 15 for x in k],
        'Close': [x + 5 for x in k],
        'Volume': [1000] * n,
    }, index=idx)


# ── yuvarlak seviyeler: sadece 100'lük, 50'lik yok ────────────
def test_yuvarlak_sadece_yuzluk_up():
    out = A.yuvarlak(4036.2, 'up', 4)
    assert out == pytest.approx([4100, 4200, 4300, 4400])


def test_yuvarlak_sadece_yuzluk_down():
    out = A.yuvarlak(4036.2, 'down', 4)
    assert out == pytest.approx([4000, 3900, 3800, 3700])


def test_yuvarlak_ellilik_seviye_uretilmez():
    """50 ile biten (4050, 4150...) hiçbir seviye dönmemeli."""
    out = A.yuvarlak(4036.2, 'up', 10) + A.yuvarlak(4036.2, 'down', 10)
    assert all(x % 100 == 0 for x in out)


def test_yuvarlak_kucuk_fiyat_yirmilik_adim():
    """500$ altında adım 20'ye düşer (ölçek korunur)."""
    out = A.yuvarlak(118.1, 'up', 3)
    assert out == pytest.approx([120, 140, 160])


# ── manşet: gram = spot / 31.1034768 * usdtry ─────────────────
def test_manset_spot_ve_gram_hesabi():
    m = A.manset(4031.70, 50.2271, 4060.0)
    assert m['kaynak_tipi'] == 'spot'
    assert m['ons'] == pytest.approx(4031.70)
    beklenen = 4031.70 / A.ONS_GRAM * 50.2271
    assert m['gram_tl'] == pytest.approx(beklenen, rel=1e-3)


def test_manset_gram_formulu_tam():
    """Kabul kriteri: gram ≈ spot/31.1035*usdtry, fark < %0,1."""
    m = A.manset(4000.0, 50.0, 3900.0)
    hesap = 4000.0 / 31.1034768 * 50.0
    assert abs(m['gram_tl'] - hesap) / hesap < 0.001


def test_manset_spot_yoksa_vadeli_rozeti():
    m = A.manset(None, 50.2271, 4060.55)
    assert m['kaynak_tipi'] == 'vadeli'
    assert m['ons'] == pytest.approx(4060.55)
    assert m['gram_tl'] is not None


def test_manset_fx_yoksa_gram_none():
    m = A.manset(4000.0, None, 3900.0)
    assert m['gram_tl'] is None


def test_manset_ons_gram_sabiti():
    """31.1034768 troy ons sabiti doğru mu (ons→gram çevrimi)."""
    assert A.ONS_GRAM == pytest.approx(31.1034768)
    m = A.manset(A.ONS_GRAM, 1.0, None)
    assert m['gram_tl'] == pytest.approx(1.0, rel=1e-6)


# ── senaryo: tetik >= 0.5×ATR, hedef >= 1×ATR ────────────────
def _vitaller(df):
    v = A.vitaller(df)
    return v, A.performans(df['Close'])


def test_senaryo_tetik_en_az_yarim_atr():
    df = _seri()
    v, perf = _vitaller(df)
    sev = A.seviyeler(df, v)
    s = A.senaryo(df, v, perf, sev)
    atr = v['atr']
    assert atr and atr > 0
    for yon in ('yukari', 'asagi'):
        tetik = s[yon]['tetik']
        assert tetik is not None, f'{yon} tetik boş'
        assert abs(tetik - v['son']) >= 0.5 * atr - 1e-6, f'{yon} tetik 0.5×ATR eşiğini geçmiyor'


def test_senaryo_hedef_tetikten_bir_atr():
    df = _seri()
    v, perf = _vitaller(df)
    sev = A.seviyeler(df, v)
    s = A.senaryo(df, v, perf, sev)
    atr = v['atr']
    for yon in ('yukari', 'asagi'):
        hedef, tetik = s[yon]['hedef'], s[yon]['tetik']
        if hedef is None:
            continue  # aday yoksa hedef boş olabilir
        assert abs(hedef - tetik) >= 1.0 * atr - 1e-6, f'{yon} hedef tetikten 1×ATR ötede değil'


def test_senaryo_gecersiz_alani_var():
    df = _seri()
    v, perf = _vitaller(df)
    sev = A.seviyeler(df, v)
    s = A.senaryo(df, v, perf, sev)
    for yon in ('yukari', 'asagi'):
        assert 'gecersiz' in s[yon], f'{yon} gecersiz alanı yok'


def test_senaryo_gecersiz_tetik_ile_tutarli():
    """Geçersizlik, tetiğin 0.5×ATR gerisinde/ilerisinde olmalı."""
    df = _seri()
    v, perf = _vitaller(df)
    s = A.senaryo(df, v, perf, A.seviyeler(df, v))
    atr = v['atr']
    gy, ta = s['yukari']['gecersiz'], s['asagi']['gecersiz']
    if gy is not None:
        assert gy < s['yukari']['tetik']
        assert abs(s['yukari']['tetik'] - gy) == pytest.approx(0.5 * atr, abs=0.2)
    if ta is not None:
        assert ta > s['asagi']['tetik']
        assert abs(ta - s['asagi']['tetik']) == pytest.approx(0.5 * atr, abs=0.2)


def test_senaryo_metin_hacim_ifadesi_yok():
    """Kodda hacim kontrolü yok → metinde 'hacimle kırıp' geçmemeli."""
    df = _seri()
    v, perf = _vitaller(df)
    s = A.senaryo(df, v, perf, A.seviyeler(df, v))
    for yon in ('yukari', 'asagi'):
        assert 'hacimle' not in s[yon]['metin'].lower()
    if s['yukari']['tetik'] and s['yukari']['hedef']:
        assert 'kırıp üstünde kapanırsa' in s['yukari']['metin']


# ── seviyeler: 50'lik yok ────────────────────────────────────
def test_seviyelerde_ellilik_yuvarlak_yok():
    df = _seri()
    v, _ = _vitaller(df)
    sev = A.seviyeler(df, v)
    yuvarlaklar = [x['seviye'] for x in sev['direnc'] + sev['destek'] if x['tip'] == 'yuvarlak']
    assert yuvarlaklar, 'hiç yuvarlak seviye yok'
    assert all(y % 100 == 0 for y in yuvarlaklar), f'100\'lük olmayan yuvarlak var: {yuvarlaklar}'


def test_seviyeler_direnc_ustte_destek_altta():
    df = _seri()
    v, _ = _vitaller(df)
    sev = A.seviyeler(df, v)
    son = v['son']
    assert all(x['seviye'] > son * 0.999 for x in sev['direnc'])
    assert all(x['seviye'] < son * 1.001 for x in sev['destek'])


# ── FOMC: tarih uydurma yok, 8-9 Aralık 2026 ─────────────────
def test_fomc_2026_aralik_karar_gunu():
    """2026 Aralık FOMC karar günü 9 Aralık (8-9 Aralık toplantısının son günü)."""
    tarihler = A.fomc_tarihleri(4000)
    iso = {t['iso'] for t in tarihler if '2026' in t['iso']}
    assert '2026-12-09' in iso, f'2026 tarihleri: {sorted(iso)}'


def test_fomc_gecmis_tarih_listelenmez():
    """Geçmiş toplantılar listeye girmez; hepsi bugünden sonra."""
    import datetime as dt
    bugun = dt.date.today().isoformat()
    tarihler = A.fomc_tarihleri(4000)
    assert tarihler
    assert all(t['iso'] >= bugun for t in tarihler), \
        f'geçmiş tarih var: {[t["iso"] for t in tarihler if t["iso"] < bugun]}'


def test_fomc_yillik_toplam_makul():
    """Her yıl ~8 toplantı × 1 karar günü; 2027 tam yıl olmalı."""
    tarihler = A.fomc_tarihleri(4000)
    y2027 = [t['iso'] for t in tarihler if t['iso'].startswith('2027')]
    assert 7 <= len(y2027) <= 9, f'2027: {len(y2027)} karar günü — beklenen ~8'


def test_fomc_pencere_disinda_da_listelenir():
    """FOMC, takvim penceresi (gun) sınırına takılmaz."""
    dar = A.fomc_tarihleri(1)
    genis = A.fomc_tarihleri(4000)
    assert len(dar) == len(genis), f'dar={len(dar)} geniş={len(genis)} — pencere sınırı uygulanmamalı'
    assert len(dar) > 0


def test_fomc_alanlari():
    tarihler = A.fomc_tarihleri(4000)
    for t in tarihler:
        assert set(t) >= {'iso', 'tarih', 'gun'}
        assert len(t['iso']) == 10 and t['iso'][4] == '-'
