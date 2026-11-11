"""G05 — BIST'e özgü filtreler. Ağ bağlantısı YOK, saf fonksiyonlar."""
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "scripts"))

from veri_cek import (  # noqa: E402
    KILIT_ESIK_PCT, LIKIDITE_ESIK_TL, IPO_GUN, RISKLI_TABAN_SAYI, RISKLI_PENCERE,
    KESIN_SAAT_TR,
    kilit_tespit, kilitli_gunler, ilk_kilitsiz, likidite_tl, ipo_bayraklari,
    taban_sayisi, riskli_tespit, sinyal_durumu,
)


def _bar(kapanis, max_=None, min_=None, hacim=1_000_000):
    return {'kapanis': kapanis,
            'max': kapanis if max_ is None else max_,
            'min': kapanis if min_ is None else min_,
            'hacim': hacim}


# ─────────────────── md.1 kilit (tavan/taban) ───────────────────

def test_tavan_kilidi_tespit():
    """Kapanış gün yükseğinde ve değişim ≥ +%9,5 → TAVAN."""
    assert kilit_tespit(_bar(110.0, 110.0, 100.0), 100.0) == 'TAVAN'


def test_taban_kilidi_tespit():
    assert kilit_tespit(_bar(90.0, 100.0, 90.0), 100.0) == 'TABAN'


def test_kilit_yok_yuksek_degil():
    """Değişim eşiği aşsa da kapanış gün yükseğinde değilse kilit yok."""
    assert kilit_tespit(_bar(110.0, 112.0, 100.0), 100.0) is None


def test_kilit_yok_esik_alti():
    assert kilit_tespit(_bar(105.0, 105.0, 100.0), 100.0) is None


def test_kilit_esik_degeri_yuzde_dokuz_bucuk():
    assert KILIT_ESIK_PCT == 9.5


def test_kilit_gecersiz_veri_none():
    assert kilit_tespit({'kapanis': None, 'max': 1, 'min': 1}, 100.0) is None
    assert kilit_tespit(_bar(110.0, 110.0, 100.0), 0) is None


def test_kilitli_gunler_sozlugu():
    rows = [_bar(100.0), _bar(110.0, 110.0, 100.0), _bar(100.0, 100.0, 100.0)]
    for i, r in enumerate(rows):
        r['tarih'] = f'2026-11-0{i + 1}'
    out = kilitli_gunler(rows)
    assert out == {'2026-11-02': 'TAVAN'}


def test_ilk_kilitsiz_kilitli_gunu_atlar():
    assert ilk_kilitsiz([1, 2, 3], {1: 'TAVAN', 2: 'TABAN'}) == 3
    assert ilk_kilitsiz([1, 2], {1: 'TAVAN', 2: 'TAVAN'}) is None
    assert ilk_kilitsiz([4], {}) == 4


# ─────────────────── md.2 likidite ───────────────────

def test_likidite_ortalama_kapanis_carpi_hacim():
    rows = [_bar(10.0, hacim=1_000_000), _bar(20.0, hacim=2_000_000)]
    # (10*1e6 + 20*2e6) / 2 = 25.000.000
    assert likidite_tl(rows) == pytest.approx(25_000_000.0)


def test_likidite_pencere_son_20_gun():
    rows = [_bar(1.0, hacim=1_000_000_000)] + [_bar(10.0, hacim=1_000_000) for _ in range(20)]
    # eski yüksek hacimli bar pencere dışında → 10.000.000
    assert likidite_tl(rows) == pytest.approx(10_000_000.0)


def test_likidite_bos_none():
    assert likidite_tl([]) is None
    assert likidite_tl(None) is None


def test_likidite_esigi_elli_milyon():
    assert LIKIDITE_ESIK_TL == 50_000_000


def test_likidite_gecersiz_bar_atlanir():
    rows = [_bar(10.0, hacim=1_000_000), {'kapanis': None, 'hacim': None}]
    assert likidite_tl(rows) == pytest.approx(10_000_000.0)


# ─────────────────── md.4 yeni halka arz ───────────────────

def test_ipo_bayrak_yeni_halka_arz():
    from datetime import date
    halka_arz = [{'kod': 'YENI1'}, {'kod': 'ESKI1'}]
    gunler = {'YENI1.IS': [str(date.today())],
              'ESKI1.IS': ['2020-01-02']}
    out = ipo_bayraklari(halka_arz, gunler)
    assert 'YENI1' in out and 'ESKI1' not in out


def test_ipo_takvimde_yoksa_bayrak_yok():
    from datetime import date
    out = ipo_bayraklari([{'kod': 'A'}], {'B': [str(date.today())]})
    assert out == {}


def test_ipo_esik_60_is_gunu():
    assert IPO_GUN == 60


def test_ipo_bos_liste():
    assert ipo_bayraklari(None, None) == {}


# ─────────────────── md.6 sorunlu hisse ───────────────────

def _taban_serisi(n):
    rows = [_bar(100.0, 100.0, 100.0)]
    fiyat = 100.0
    for _ in range(n):
        fiyat *= 0.90
        rows.append(_bar(fiyat, fiyat + 5, fiyat))
    return rows


def test_taban_sayisi_seri():
    assert taban_sayisi(_taban_serisi(3)) == 3


def test_riskli_tespit_uc_taban():
    gerekce = riskli_tespit(_taban_serisi(3))
    assert gerekce is not None and '3 taban' in gerekce


def test_riskli_tespit_iki_taban_yetmez():
    assert riskli_tespit(_taban_serisi(2)) is None


def test_riskli_esikleri():
    assert RISKLI_TABAN_SAYI == 3
    assert RISKLI_PENCERE == 10


def test_riskli_bos_veri():
    assert riskli_tespit([]) is None
    assert taban_sayisi([]) == 0


# ─────────────────── md.3 sinyal kesinliği (18:15 TR) ───────────────────

def test_sinyal_durumu_kapanis_sonrasi_kesin():
    from datetime import datetime, timezone, timedelta
    tr = timezone(timedelta(hours=3))
    assert sinyal_durumu(datetime(2026, 11, 11, 18, 30, tzinfo=tr)) == 'kesin'


def test_sinyal_durumu_seans_ici_gecici():
    from datetime import datetime, timezone, timedelta
    tr = timezone(timedelta(hours=3))
    assert sinyal_durumu(datetime(2026, 11, 11, 14, 0, tzinfo=tr)) == 'gecici'


def test_kesin_saat_degeri():
    assert KESIN_SAAT_TR == 18.25
