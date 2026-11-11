#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G13 — TR risk ve reel BIST saf fonksiyon testleri (ağa çıkmaz)."""
import datetime as dt
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import veri_cek as v  # noqa: E402


def _seri(baslangic, n, fiyat=lambda i: 100.0 + i, adim=1):
    return [(baslangic + dt.timedelta(days=i * adim), fiyat(i)) for i in range(n)]


# ── tarihe göre hizalama ──────────────────────────────────────
def test_seri_eslestir_hafta_sonu_boslugu_tolere_eder():
    ana = [(dt.date(2026, 1, 5), 10.0), (dt.date(2026, 1, 12), 11.0)]   # pazartesiler
    diger = [(dt.date(2026, 1, 2), 30.0), (dt.date(2026, 1, 9), 31.0)]  # cumalar
    out = v.seri_eslestir(ana, diger)
    assert len(out) == 2
    assert out[0] == (dt.date(2026, 1, 5), [10.0, 30.0])      # 3 gün önceki cuma
    assert out[1][1] == [11.0, 31.0]


def test_seri_eslestir_tolerans_asilirsa_gun_duser():
    ana = [(dt.date(2026, 1, 5), 10.0)]
    diger = [(dt.date(2025, 12, 20), 30.0)]                    # 16 gün önce > 7
    assert v.seri_eslestir(ana, diger) == []


def test_seri_eslestir_indexe_gore_degil_tarihe_gore():
    """Aynı index farklı tarih: hizalama tarihe göre olmalı."""
    ana = [(dt.date(2026, 3, 2), 1.0), (dt.date(2026, 3, 3), 2.0)]
    diger = [(dt.date(2026, 2, 1), 100.0), (dt.date(2026, 3, 3), 200.0)]
    out = v.seri_eslestir(ana, diger)
    assert out == [(dt.date(2026, 3, 3), [2.0, 200.0])]


def test_seri_eslestir_ileri_tarih_kullanilmaz():
    """Hedef tarihten SONRAKİ değer baz alınmaz (bakış ileri sızıntısı yok)."""
    ana = [(dt.date(2026, 1, 5), 10.0)]
    diger = [(dt.date(2026, 1, 6), 99.0)]
    assert v.seri_eslestir(ana, diger) == []


# ── reel seriler ──────────────────────────────────────────────
def test_reel_bist_serileri_usd_ve_altin_orani():
    xu = _seri(dt.date(2026, 1, 1), 3, lambda i: 100.0 + 10 * i)
    kur = _seri(dt.date(2026, 1, 1), 3, lambda i: 30.0)
    gram = _seri(dt.date(2026, 1, 1), 3, lambda i: 2000.0)
    s = v.reel_bist_serileri(xu, kur, gram)
    assert s['durum'] == 'ok'
    assert s['usd'][0][1] == round(100 / 30, 4)
    assert s['altin'][0][1] == round(100 / 2000, 4)
    assert s['bas'] == '2026-01-01' and s['son'] == '2026-01-03'


def test_reel_bist_serileri_ortak_gun_yoksa_veri_yok():
    xu = _seri(dt.date(2026, 1, 1), 2, adim=1)
    kur = [(dt.date(2025, 1, 1), 30.0)]
    s = v.reel_bist_serileri(xu, kur, kur)
    assert s['durum'] == 'veri yok' and s['hizalama']['eslesen_gun'] == 0


# ── getiriler ────────────────────────────────────────────────
def _reel_seri(n, xu_fiyat, kur_fiyat, gram_fiyat, bas=dt.date(2026, 1, 1)):
    xu = _seri(bas, n, xu_fiyat)
    kur = _seri(bas, n, kur_fiyat)
    gram = _seri(bas, n, gram_fiyat)
    return v.reel_bist_serileri(xu, kur, gram)


def test_getiri_ybb_ve_tl_artisi():
    s = _reel_seri(30, lambda i: 100.0 + i, lambda i: 30.0, lambda i: 3000.0)
    g = v.reel_bist_getirileri(s)
    ybb = g['donemler']['ybb']
    assert ybb['tl'] == pytest.approx((129 / 100 - 1) * 100, abs=1e-2)
    assert ybb['bas_tarih'] == '2026-01-01'


def test_getiri_tutarlilik_usd_ile_uyusuyor():
    s = _reel_seri(30, lambda i: 100.0 + 2 * i, lambda i: 30.0 + 0.1 * i, lambda i: 3000.0)
    g = v.reel_bist_getirileri(s)
    t = [x for x in g['tutarlilik'] if x['donem'] == 'ybb'][0]
    assert t['esik_pct'] == 0.1
    assert abs(t['fark_pct']) <= 0.1
    assert t['ok'] is True


def test_getiri_pencere_yetmezse_veri_yok():
    s = _reel_seri(10, lambda i: 100.0 + i, lambda i: 30.0, lambda i: 3000.0)
    d = v.reel_bist_getirileri(s)['donemler']
    assert d['1y']['tl'] is None
    assert 'tl' in d['1y']['eksik']
    assert d['1h']['tl'] is not None


def test_getiri_son_gun_katı_eslesme():
    """Seride son tarih hedefle birebir eşleşmezse getiri üretilmez."""
    seri = [(dt.date(2026, 1, 1), 100.0), (dt.date(2026, 1, 5), 110.0)]
    assert v._g13_getiri(seri, dt.date(2026, 1, 6), dt.date(2026, 1, 1)) is None
    assert v._g13_getiri(seri, dt.date(2026, 1, 5), dt.date(2026, 1, 1)) is not None


def test_pencere_bar_sayilari():
    assert v.G13_DONEM_BAR == {'1h': 5, '1a': 21, '3a': 63, '1y': 252}


# ── reel faiz ────────────────────────────────────────────────
def test_reel_faiz_pozitif():
    assert v.reel_faiz(36.0, 29.77) == 6.23


def test_reel_faiz_negatif():
    assert v.reel_faiz(20.0, 35.5) == -15.5


@pytest.mark.parametrize('p, t', [(None, 30.0), (30.0, None), ('abc', 30.0), (float('nan'), 30.0)])
def test_reel_faiz_eksik_girdi_none(p, t):
    assert v.reel_faiz(p, t) is None


# ── tahvil ───────────────────────────────────────────────────
def test_tahvil_2y_10y_ayiklanir():
    b = v.tahvil_getirileri({'tahvil': [{'vade': '2Y', 'getiri': 39.42},
                                        {'vade': '5Y', 'getiri': 39.03},
                                        {'vade': '10Y', 'getiri': 35.99}]})
    assert b['2Y'] == 39.42 and b['10Y'] == 35.99 and 'eksik' not in b


def test_tahvil_yoksa_durum_gosterilir():
    b = v.tahvil_getirileri({'tahvil': [], 'tahvil_durum': 'kaynak kapalı'})
    assert b['2Y'] is None and b['10Y'] is None
    assert b['durum'] == 'kaynak kapalı' and b['eksik'] == ['2Y', '10Y']


def test_tahvil_eksik_vade_notu():
    b = v.tahvil_getirileri({'tahvil': [{'vade': '2Y', 'getiri': 39.0}]})
    assert b['10Y'] is None and b['eksik'] == ['10Y']


# ── PPK parse ────────────────────────────────────────────────
PPK_HTML = """
<html><body><table>
<tr><th>Karar Tarihi</th><th>Karar</th></tr>
<tr><td>22 Ocak 2026</td><td>Faiz sabit</td></tr>
<tr><td>10 Aralık 2026</td><td>Faiz sabit</td></tr>
<tr><td>21 Ocak 2027</td><td>-</td></tr>
</table></body></html>
"""


def test_ppk_parse_yalniz_hedef_yil():
    got = v.ppk_tarihleri_parse(PPK_HTML, 2026)
    assert got == ['2026-01-22', '2026-12-10']
    assert v.ppk_tarihleri_parse(PPK_HTML, 2027) == ['2027-01-21']


def test_ppk_parse_tablo_yoksa_bos():
    assert v.ppk_tarihleri_parse('<html><body>Duyuru yok</body></html>', 2026) == []
    assert v.ppk_tarihleri_parse('', 2026) == []


def test_ppk_parse_tarih_uydurmaz():
    """Metinde yıl geçse de tablo tarihi yoksa tarih üretilmez."""
    assert v.ppk_tarihleri_parse('<p>2027 toplantı takvimi yakında</p>', 2027) == []


def test_sonraki_ppk_geri_sayim():
    s = v.sonraki_ppk(['2026-01-22', '2026-12-10'], dt.date(2026, 11, 12))
    assert s == {'tarih': '2026-12-10', 'kalan_gun': 28}


def test_sonraki_ppk_yoksa_veri_yok():
    s = v.sonraki_ppk(['2026-01-22'], dt.date(2026, 11, 12))
    assert s['durum'] == 'veri yok'
    assert 'tarih' not in s


# ── risk bloğu (rezerv / CDS) ────────────────────────────────
def test_risk_blogu_rezerv_anahtar_yok(monkeypatch):
    monkeypatch.delenv('EVDS_KEY', raising=False)
    b = v.makro_risk_blogu({'tahvil': []}, {'faiz': 36.0, 'tarih': '23.10.2026'},
                           {'yillik': 29.77, 'tarih': '10-2026'})
    assert b['rezerv']['durum'] == 'anahtar yok'
    assert b['rezerv']['secret'] == 'EVDS_KEY'
    assert 'anahtar yok' in b['rezerv']['metin']
    assert b['cds']['durum'] == 'eklenmedi'
    assert b['reel_faiz']['deger'] == 6.23
    assert 'POZİTİF' in b['reel_faiz']['yorum']


def test_risk_blogu_eksik_veride_sayi_uydurmaz(monkeypatch):
    monkeypatch.delenv('EVDS_KEY', raising=False)
    b = v.makro_risk_blogu({'tahvil': []}, {}, {})
    assert b['reel_faiz']['deger'] is None
    assert b['reel_faiz']['yorum'] is None
    assert b['politika']['durum'] == 'veri yok'
    assert b['tufe']['durum'] == 'veri yok'


def test_risk_blogu_tahvil_yoksa_tahvil_durum_gosterilir(monkeypatch):
    monkeypatch.delenv('EVDS_KEY', raising=False)
    b = v.makro_risk_blogu({'tahvil': [], 'tahvil_durum': 'boş'}, {'faiz': 36.0}, {'yillik': 30.0})
    assert b['tahvil']['goster'] == 'tahvil_durum'
    assert 'boş' in b['tahvil']['metin']
