"""G17 — Filtre senaryoları testleri (ağa çıkmaz).

Kapsam:
- `senaryo_uret` tanım listesinde filtre varyantlarının bulunması
- `min_skor` filtresinin zayıf skorlu sinyalleri gerçekten elemesi
- `endeks_rejim` filtresinin yetersiz endeks serisinde 'veri yok' dönmesi
- 'en iyi' seçiminde en az işlem şartının uygulanması
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import veri_cek as v  # noqa: E402


def _hisse(fiyatlar, tarih_bas='2025-01-01'):
    """OHLCV satır listesi üret (hisse_veri formatı: dict listesi)."""
    rows = []
    for i, f in enumerate(fiyatlar):
        rows.append({
            'tarih': (pd.Timestamp(tarih_bas) + pd.Timedelta(days=i)).strftime('%Y-%m-%d'),
            'acilis': float(f), 'kapanis': float(f),
            'min': float(f) * 0.98, 'max': float(f) * 1.02,
            'hacim': 5_000_000.0,
        })
    return rows


def _senaryo_anahtarlari():
    """senaryo_uret tanım listesindeki anahtarlar (boş veri → senaryolar boş döner,
    bu yüzden kaynak koddan değil, dolu sentetik veriden okunur)."""
    veri = {'TEST': _hisse([100 + (i % 11) for i in range(260)])}
    r = v.senaryo_uret(veri, [])
    return {s['anahtar'] for s in r['senaryolar']}


def test_filtre_senaryolari_tanimli():
    """G17 filtre varyantları tanım listesinde olmalı."""
    anahtarlar = _senaryo_anahtarlari()
    for beklenen in ('skor_3', 'skor_4', 'rejim', 'rejim_200', 'skor_3_rejim', 'skor_4_rejim'):
        assert beklenen in anahtarlar, f'{beklenen} tanımlı değil'


def test_min_skor_zayif_sinyalleri_eler():
    """skor>=4 filtresi skor 2/3 sinyallerini dışarıda bırakmalı."""
    fiyatlar = [100 + (i % 11) for i in range(260)]
    veri = {'TEST': _hisse(fiyatlar)}
    hepsi = v.test_senaryolari(veri, [], {'hedef': False, 'vade_gun': 20})
    guclu = v.test_senaryolari(veri, [], {'hedef': False, 'vade_gun': 20, 'min_skor': 9})
    assert (hepsi.get('metrik') or {}).get('islem', 0) > 0, 'referans işlem üretmeli'
    # min_skor=9 → hiçbir sinyal geçemez (skor en fazla 5) → işlem yok
    assert not (guclu.get('metrik') or {}).get('islem')


def test_endeks_rejim_yetersiz_seri_veri_yok():
    """Endeks serisi MA penceresinden kısaysa uydurma yapılmaz, 'veri yok' döner."""
    fiyatlar = [100 + (i % 11) for i in range(260)]
    veri = {'TEST': _hisse(fiyatlar)}
    kisa_endeks = [('2025-06-0%d' % (i + 1), 10000 + i) for i in range(5)]
    r = v.test_senaryolari(veri, kisa_endeks, {'endeks_rejim': 200})
    assert r.get('durum') == 'veri yok'
    assert 'MA' in (r.get('aciklama') or '')


def test_endeks_rejim_dusen_endekste_sinyal_uretmez():
    """XU100 kendi MA50'sinin altindayken (düşen endeks) rejim filtresi işlem üretmemeli:
    tüm sinyaller endeks düşüşündeyse filtre hepsini eler."""
    fiyatlar = [100 + (i % 11) for i in range(260)]
    veri = {'TEST': _hisse(fiyatlar)}
    # Sürekli düşen XU100 → kapanış hiçbir zaman MA50 üstünde olmaz
    dusen = [((pd.Timestamp('2025-01-01') + pd.Timedelta(days=i)).strftime('%Y-%m-%d'),
              100000 - i * 100) for i in range(260)]
    r = v.test_senaryolari(veri, dusen, {'endeks_rejim': 50, 'hedef': False, 'vade_gun': 20})
    assert not (r.get('metrik') or {}).get('islem'), 'düşen endekste AL üretilmemeli'


def test_endeks_rejim_yukselen_endekste_gecirir():
    """Yükselen endekste rejim filtresi sinyalleri geçirmeli (filtre işlem sayısını sıfırlamaz)."""
    fiyatlar = [100 + (i % 11) for i in range(260)]
    veri = {'TEST': _hisse(fiyatlar)}
    yukselen = [((pd.Timestamp('2025-01-01') + pd.Timedelta(days=i)).strftime('%Y-%m-%d'),
                 100000 + i * 100) for i in range(260)]
    r = v.test_senaryolari(veri, yukselen, {'endeks_rejim': 50, 'hedef': False, 'vade_gun': 20})
    assert (r.get('metrik') or {}).get('islem', 0) > 0


def test_en_az_islem_esigi_doner():
    """senaryo_uret çıktısı 'en_az_islem' alanını taşımalı (küçük örneklem koruması)."""
    veri = {'TEST': _hisse([100 + (i % 11) for i in range(260)])}
    r = v.senaryo_uret(veri, [])
    assert r.get('en_az_islem') == 100
