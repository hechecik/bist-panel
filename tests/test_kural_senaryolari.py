"""G16 — Kural senaryoları testleri (ağa çıkmaz).

Amaç: `senaryo_uret` ve `_islem_hesapla(..., kural)` davranışının doğrulanması.
Sentetik fiyat serisi kullanılır; gerçek ağ çağrısı yapılmaz.
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import veri_cek as v  # noqa: E402


def _seri(fiyatlar):
    """OHLCV tablosu üret — fiyatlar kapanış listesi; tarih index olarak KALIR
    (`_islem_hesapla`/`_bar_fiyat` `HGDG_TARIH` sütununu index bekliyor)."""
    idx = []
    for i, f in enumerate(fiyatlar):
        idx.append({
            'HGDG_TARIH': pd.Timestamp('2026-01-01') + pd.Timedelta(days=i),
            'HGDG_ACILIS': float(f),
            'HGDG_KAPANIS': float(f),
            'HGDG_MAX': float(f) * 1.01,
            'HGDG_MIN': float(f) * 0.99,
            'HGDG_HACIM': 1_000_000.0,
            'ATR14': float(f) * 0.02,
        })
    return pd.DataFrame(idx)


def test_senaryo_tanimlari_var():
    """senaryo_uret boş veride çökmemeli ve yapı dönmeli."""
    r = v.senaryo_uret({}, None)
    assert 'senaryolar' in r
    assert r['senaryolar'] == []


def test_kural_varsayilan_davranisi_degistirmez():
    """kural=None ile kural={} aynı sonucu vermeli (geriye uyumluluk)."""
    fiyatlar = [100 + (i % 7) - 3 for i in range(260)]
    ind = _seri(fiyatlar)
    s = {'skor': 4, 'sinyal': 'AL'}
    kilitler = {}
    a = v._islem_hesapla('TEST', 200, s, ind, kilitler)
    b = v._islem_hesapla('TEST', 200, s, ind, kilitler, {})
    if a is None:
        assert b is None
        return
    assert a['giris_tarih'] == b['giris_tarih']
    assert a['getiri_yuzde'] == b['getiri_yuzde']


def test_vade_gun_kurali_islem_vadesini_kisaltir():
    """vade_gun=5 verilince işlem en fazla 5 iş günü sürmeli."""
    fiyatlar = [100 + (i % 5) for i in range(300)]
    ind = _seri(fiyatlar)
    s = {'skor': 4, 'sinyal': 'AL'}
    uzun = v._islem_hesapla('TEST', 200, s, ind, {}, {'stop': False, 'hedef': False})
    kisa = v._islem_hesapla('TEST', 200, s, ind, {}, {'stop': False, 'hedef': False, 'vade_gun': 5})
    assert kisa is not None
    assert kisa['vade_gun'] <= 5
    if uzun is not None:
        assert kisa['vade_gun'] <= uzun['vade_gun']


def test_stop_kapali_uzun_kaybi_kesmez():
    """Sürekli düşen seride stopsuz senaryo stoplu senaryodan daha kötü olmalı.
    Düşüş 2×ATR stop mesafesinden büyük seçilir (%3/gün), yoksa stop hiç tetiklenmez."""
    fiyatlar = [300 * (0.97 ** i) for i in range(300)]
    ind = _seri(fiyatlar)
    s = {'skor': 4, 'sinyal': 'AL'}
    stoplu = v._islem_hesapla('TEST', 200, s, ind, {})
    stopsuz = v._islem_hesapla('TEST', 200, s, ind, {}, {'stop': False})
    assert stoplu is not None and stopsuz is not None
    assert stoplu['cikis_neden'] == 'stop'
    assert stopsuz['getiri_yuzde'] < stoplu['getiri_yuzde']


def test_senaryo_uretim_anahtarlari():
    """Tanımlı senaryo anahtarları sabit olmalı (UI bunlara göre çiziyor)."""
    beklenen = {'referans', 'stop_yok', 'hedef_yok', 'cikis_yok',
                'vade_5', 'vade_10', 'vade_20', 'kapanis_giris'}
    kaynak = open(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'veri_cek.py'),
                  encoding='utf-8').read()
    for k in beklenen:
        assert f"('{k}'" in kaynak, f'senaryo tanımı eksik: {k}'
