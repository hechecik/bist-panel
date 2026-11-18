"""G15 — Fon kategori top-10 yapısı testleri (ağa çıkmaz)."""
import json
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent


def test_katalog_946_fon():
    kat = json.loads((KOK / 'fonlar-katalog.json').read_text(encoding='utf-8'))
    assert len(kat) == 946
    assert all(x['kod'] and x['ad'] for x in kat)
    assert len({x['kod'] for x in kat}) == 946  # kod tekrarı yok


def test_kategori_sirasi_ve_sayisi():
    import sys
    sys.path.insert(0, str(KOK / 'scripts'))
    import veri_cek as v
    assert len(v.FON_KATEGORILERI) == 9
    adlar = [a for _, a in v.FON_KATEGORILERI]
    assert len(set(adlar)) == 9
    assert v.FON_TOP_N == 10
    assert v.FON_MIN_BUYUKLUK == 50_000_000


def test_kategori_tipi_katalogla_uyumlu():
    """FON_KATEGORILERI'ndeki TEFAS tipleri taramada gerçekten görülen tipler olmalı."""
    import sys
    sys.path.insert(0, str(KOK / 'scripts'))
    import veri_cek as v
    tipler = {t for t, _ in v.FON_KATEGORILERI}
    assert 'Kıymetli Madenler Şemsiye Fonu' in tipler
    assert 'Hisse Senedi Şemsiye Fonu' in tipler
    # Her tip 'Şemsiye Fonu' ile bitmeli (TEFAS'ın kendi adlandırması)
    assert all(t.endswith('Şemsiye Fonu') for t in tipler)
    assert v.FON_TIP_ADI['Kıymetli Madenler Şemsiye Fonu'] == '🥇 Altın & Kıymetli Maden'


def test_fonlar_cek_katalog_yoksa_bos_doner(monkeypatch, tmp_path):
    """Katalog okunamazsa çökmemeli, boş yapı dönmeli."""
    import sys
    sys.path.insert(0, str(KOK / 'scripts'))
    import veri_cek as v
    monkeypatch.setattr(v.Path, 'resolve', lambda self: tmp_path / 'x' / 'y')
    r = v.fonlar_cek({})
    assert r['kategoriler'] == []
    assert r['fonlar'] == []


def test_onceki_veri_korunur_yapisi():
    """TEFAS düşerse önceki kategoriler korunur ve bayat=True işaretlenir."""
    import sys
    sys.path.insert(0, str(KOK / 'scripts'))
    import veri_cek as v

    class SahteFund:
        def __init__(self, kod):
            raise RuntimeError('TEFAS yok')

    import borsapy
    eski_fund = borsapy.Fund
    borsapy.Fund = SahteFund
    try:
        onceki = {'kategoriler': [{'ad': 'X', 'tip': 'T', 'fon_sayisi': 1, 'top': []}],
                  'tarih': '2026-01-01', 'siralama_notu': 'eski not'}
        r = v.fonlar_cek(onceki)
        assert r['kategoriler'] == onceki['kategoriler']
        assert r['bayat'] is True
        assert r['tarih'] == '2026-01-01'
    finally:
        borsapy.Fund = eski_fund
