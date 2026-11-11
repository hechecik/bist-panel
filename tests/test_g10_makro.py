#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G10 — makro katmanı saf fonksiyon testleri (ağa çıkmaz)."""
import datetime as dt
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import altin_cek as a  # noqa: E402


# ── korelasyon ────────────────────────────────────────────────
def test_korelasyon_mukemmel_pozitif():
    gun = dt.date(2026, 1, 1)
    ser = [(gun + dt.timedelta(days=i), float(i)) for i in range(70)]
    k = a.rolling_korelasyon(ser, ser, 60)
    assert k is not None
    assert k[0] == 1.0
    assert k[1] == 60


def test_korelasyon_mukemmel_negatif():
    gun = dt.date(2026, 1, 1)
    x = [(gun + dt.timedelta(days=i), float(i)) for i in range(70)]
    y = [(gun + dt.timedelta(days=i), float(-2 * i)) for i in range(70)]
    k = a.rolling_korelasyon(x, y, 60)
    assert k[0] == -1.0


def test_korelasyon_az_veri_none():
    gun = dt.date(2026, 1, 1)
    x = [(gun + dt.timedelta(days=i), float(i)) for i in range(5)]
    assert a.rolling_korelasyon(x, x, 60) is None


def test_korelasyon_duz_seri_none():
    """Varyansı sıfır olan seride korelasyon tanımsız → None (0'a bölme yok)."""
    gun = dt.date(2026, 1, 1)
    x = [(gun + dt.timedelta(days=i), 5.0) for i in range(70)]
    y = [(gun + dt.timedelta(days=i), float(i)) for i in range(70)]
    assert a.rolling_korelasyon(x, y, 60) is None


def test_korelasyon_tarih_hizalar():
    """FRED ve piyasa takvimleri farklı: yalnız ortak günler kullanılmalı."""
    gun = dt.date(2026, 1, 1)
    ortak = [(gun + dt.timedelta(days=i), float(i)) for i in range(40, 100)]
    ekstra = [(gun + dt.timedelta(days=i), 999.0) for i in range(0, 40)]
    k = a.rolling_korelasyon(ortak + ekstra, ortak, 60)
    assert k[1] == 60
    assert k[0] == 1.0


def test_korelasyon_pencere_keser():
    gun = dt.date(2026, 1, 1)
    x = [(gun + dt.timedelta(days=i), float(i)) for i in range(200)]
    assert a.rolling_korelasyon(x, x, 30)[1] == 30


# ── seri özeti ────────────────────────────────────────────────
def test_seri_ozet_bos():
    assert a.seri_ozet([]) == {'durum': 'veri yok'}


def test_seri_ozet_degisimler():
    gun = dt.date(2026, 1, 1)
    ser = [(gun + dt.timedelta(days=i), 10.0 + i) for i in range(30)]
    oz = a.seri_ozet(ser)
    assert oz['son'] == 39.0
    assert oz['degisim_5g'] == 5.0      # bugün - 5 gün önce
    assert oz['degisim_20g'] == 20.0
    assert oz['korelasyon_60g'] is None  # ons verilmedi


def test_seri_ozet_altin_korelasyon():
    gun = dt.date(2026, 1, 1)
    ser = [(gun + dt.timedelta(days=i), 10.0 + i * 0.5) for i in range(90)]
    ons = [(gun + dt.timedelta(days=i), 100.0 + i * 2) for i in range(90)]
    oz = a.seri_ozet(ser, ons)
    assert oz['korelasyon_60g'] == 1.0
    assert oz['korelasyon_gun'] == 60


# ── makas yorumu ──────────────────────────────────────────────
@pytest.mark.parametrize('bp,beklenen', [
    (26, 'şahin'), (-26, 'güvercin'), (25, 'Uyumlu'), (-25, 'Uyumlu'),
    (0, 'Uyumlu'), (56, 'şahin'), (-120, 'güvercin'),
])
def test_makas_yorumu(bp, beklenen):
    assert beklenen.lower() in a.makas_yorumu(bp).lower()


def test_makas_yorumu_veri_yok():
    assert a.makas_yorumu(None) == 'veri yok'


# ── SEP revizyon ──────────────────────────────────────────────
def test_sep_revizyon_sahin():
    r = a.sep_revizyon(4.1, 4.4)
    assert r['degisim_bp'] == 30
    assert r['yorum'] == 'şahin revizyon'


def test_sep_revizyon_guvercin():
    r = a.sep_revizyon(4.1, 3.8)
    assert r['degisim_bp'] == -30
    assert r['yorum'] == 'güvercin revizyon'


def test_sep_revizyon_esik_alti():
    r = a.sep_revizyon(4.1, 4.2)
    assert r['degisim_bp'] == 10
    assert r['yorum'] == 'değişim yok'


def test_sep_revizyon_veri_yok():
    assert a.sep_revizyon(None, 4.1)['yorum'] == 'veri yok'


# ── ET → TSİ ──────────────────────────────────────────────────
def test_fomc_tsi_kis_saati():
    """9 Aralık 2026: ABD kış saati → 14:00 ET = 22:00 TSİ (kabul kriteri)."""
    t = a.fomc_tsi('2026-12-09')
    assert t['saat_kisa'] == '22:00'
    assert t['tsi'] == '09.12.2026 22:00'


def test_fomc_tsi_yaz_saati():
    """Haziran: ABD yaz saati → 14:00 ET = 21:00 TSİ. Sabit 22:00 yazılmaz."""
    assert a.fomc_tsi('2026-06-17')['saat_kisa'] == '21:00'


def test_fomc_tsi_gecis_aylari():
    """Mart başı kış (22:00), mart sonu yaz (21:00); ekim sonu yaz, kasım başı kış."""
    assert a.fomc_tsi('2026-03-01')['saat_kisa'] == '22:00'
    assert a.fomc_tsi('2026-03-20')['saat_kisa'] == '21:00'
    # ABD yaz saati 2026'da 1 Kasım'da bitti → 1 Kasım artık kış saati
    assert a.fomc_tsi('2026-10-28')['saat_kisa'] == '21:00'
    assert a.fomc_tsi('2026-11-01')['saat_kisa'] == '22:00'


def test_fomc_tsi_utc_dogru():
    # 14:00 ET kış = 19:00 UTC
    assert a.fomc_tsi('2026-12-09')['iso_utc'].startswith('2026-12-09T19:00')


# ── FOMC sayacı ───────────────────────────────────────────────
def test_fomc_sayac_metin():
    simdi = dt.datetime(2026, 11, 11, 12, 0, tzinfo=dt.timezone.utc)
    s = a.fomc_sayac('2026-12-09', True, simdi)
    assert s['tarih'] == '09.12.2026'
    assert s['saat_tsi'] == '22:00'
    assert s['kalan_gun'] == 28
    assert s['sep'] is True
    assert 'SEP/dot plot VAR' in s['metin']


def test_fomc_sayac_gecmis_sifirlanir():
    simdi = dt.datetime(2027, 1, 1, tzinfo=dt.timezone.utc)
    s = a.fomc_sayac('2026-12-09', False, simdi)
    assert s['kalan_gun'] == 0


def test_fomc_sayac_veri_yok():
    assert a.fomc_sayac(None)['durum'] == 'veri yok'


# ── fed funds ima patikası ────────────────────────────────────
def test_ima_faiz_100_eksi_fiyat():
    r = a.fed_fonlari_ima([{'ay': '2026-12', 'fiyat': 95.92}])
    assert r['kontratlar'][0]['ima'] == pytest.approx(4.08)


def test_ima_yil_sonu_son_kontrat():
    aylar = [{'ay': '2026-11', 'fiyat': 96.12}, {'ay': '2026-12', 'fiyat': 95.92},
             {'ay': '2027-06', 'fiyat': 95.37}, {'ay': '2027-12', 'fiyat': 95.10}]
    r = a.fed_fonlari_ima(aylar)
    assert r['yillar'][2026] == pytest.approx(4.08)
    assert r['yillar'][2027] == pytest.approx(4.90)
    assert r['kaynak'] == 'vadeli'


def test_ima_bos():
    assert a.fed_fonlari_ima([]) is None
    assert a.fed_fonlari_ima(None) is None


def test_ima_fiyatsiz_kontrat_atlanir():
    r = a.fed_fonlari_ima([{'ay': '2026-12', 'fiyat': None}])
    assert r is None


# ── kaynak kodda elle girilmiş değer yok ──────────────────────
def test_kodda_elle_faiz_yok():
    """Kabul kriteri: kodda elle girilmiş faiz/hedef değeri bulunmamalı."""
    yol = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'altin_cek.py')
    with open(yol, encoding='utf-8') as f:
        kod = f.read()
    makro = kod[kod.index('# 5b) MAKRO SÜRÜCÜLER'):kod.index('# 6) HABERLER')]
    for yasak in ['4.25', '4.50', '5.50', '3.50', 'olasilik =', 'hedef_faiz =']:
        assert yasak not in makro, f'makro bloğunda elle girilmiş değer: {yasak}'
