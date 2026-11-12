"""Eksik hisse teşhisi + yfinance tamamlama testleri (ağsız).

Kapsam:
- `veri_saglik_kontrolu`: eksik hisse listesi/nedeni → UYARI + banner verisi
- `tamamla_yfinance`: sadece eksikleri çeker, `kaynak='yfinance'` yazar
- `cek_borsapy` neden loglama: boş yanıt / az bar / sembol hatası
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import veri_cek as vc  # noqa: E402


def _rows(n=80, son_fiyat=100.0):
    return [{'tarih': f'2026-01-{i % 28 + 1:02d}', 'kapanis': son_fiyat,
             'acilis': son_fiyat, 'min': son_fiyat, 'max': son_fiyat, 'hacim': 1_000_000}
            for i in range(n)]


# ── sağlık kontrolü ─────────────────────────────────────────────────────────
def test_saglik_tam_liste_ok():
    veri = {s: _rows() for s in [f"H{i:03d}" for i in range(100)]}
    saglik = vc.veri_saglik_kontrolu(veri, {'deger': 11000}, 'borsapy-tv')
    assert saglik['durum'] == 'OK'
    assert saglik['hisse'] == 100
    assert saglik['eksik_hisseler'] == []
    assert saglik['kaynak_dagilim'] == {'bilinmiyor': 100}


def test_saglik_99_hisse_uyari():
    """99 hisse → UYARI (eskiden <80 eşiği vardı, 91 hisse OK görünüyordu)."""
    veri = {s: _rows() for s in [f"H{i:03d}" for i in range(99)]}
    saglik = vc.veri_saglik_kontrolu(veri, {'deger': 11000}, 'borsapy-tv')
    assert saglik['durum'] == 'UYARI'
    assert any('99/100' in s for s in saglik['sorunlar'])


def test_saglik_eksik_hisse_listesi_ve_nedeni():
    veri = {f"H{i:03d}": _rows() for i in range(97)}
    eksik = ['GARAN', 'THYAO', 'ZOREN']
    nedenler = {'GARAN': 'az bar (12 bar)', 'THYAO': 'boş yanıt', 'ZOREN': 'sembol/istisna'}
    saglik = vc.veri_saglik_kontrolu(veri, {'deger': 11000}, 'borsapy-tv',
                                     eksik_hisseler=eksik, eksik_nedenler=nedenler)
    assert saglik['durum'] == 'UYARI'
    assert saglik['eksik_hisseler'] == eksik
    assert saglik['eksik_nedenler']['GARAN'] == 'az bar (12 bar)'
    satir = [s for s in saglik['sorunlar'] if 'hisse çekilemedi' in s][0]
    assert 'GARAN(az bar (12 bar))' in satir
    assert 'THYAO(boş yanıt)' in satir


def test_saglik_kaynak_dagilim():
    veri = {f"H{i:03d}": _rows() for i in range(95)}
    for s in ['H095', 'H096']:
        veri[s] = [dict(r, kaynak='yfinance') for r in _rows()]
    saglik = vc.veri_saglik_kontrolu(veri, {'deger': 11000}, 'borsapy-tv')
    assert saglik['kaynak_dagilim'].get('yfinance') == 2
    assert saglik['kaynak_dagilim'].get('bilinmiyor') == 95


def test_saglik_kritik_50_alti():
    veri = {f"H{i:03d}": _rows() for i in range(40)}
    saglik = vc.veri_saglik_kontrolu(veri, {'deger': 11000}, 'borsapy-tv',
                                     eksik_hisseler=[f"E{i}" for i in range(60)])
    assert saglik['durum'] == 'KRİTİK'


# ── yfinance tamamlama ──────────────────────────────────────────────────────
def test_tamamla_yfinance_sadece_eksikleri_ceker(monkeypatch):
    cagrilan = []

    def sahte_cek(sym):
        cagrilan.append(sym)
        if sym == 'ZOREN':
            return None, vc.LOG_NEDEN_BOS_YANIT
        return _rows(70), None

    monkeypatch.setattr(vc, 'cek_yfinance_tek', sahte_cek)
    hisse_veri = {'GARAN': _rows()}
    nedenler = {}
    eklenen, kalan = vc.tamamla_yfinance(hisse_veri, ['THYAO', 'ZOREN'], nedenler=nedenler)

    assert cagrilan == ['THYAO', 'ZOREN']           # mevcut hisse tekrar çekilmedi
    assert eklenen == ['THYAO']
    assert kalan == ['ZOREN']
    assert nedenler == {'ZOREN': vc.LOG_NEDEN_BOS_YANIT}
    assert all(r['kaynak'] == 'yfinance' for r in hisse_veri['THYAO'])   # kaynak izlenebilirliği
    assert 'kaynak' not in hisse_veri['GARAN'][0]                        # mevcut veri bozulmadı


def test_tamamla_yfinance_eksik_yok():
    hisse_veri = {'GARAN': _rows()}
    assert vc.tamamla_yfinance(hisse_veri, ['GARAN']) == ([], [])


def test_tamamla_yfinance_hepsi_basarisiz(monkeypatch):
    monkeypatch.setattr(vc, 'cek_yfinance_tek', lambda s: (None, vc.LOG_NEDEN_AZ_BAR))
    eklenen, kalan = vc.tamamla_yfinance({}, ['A', 'B'])
    assert eklenen == [] and kalan == ['A', 'B']


# ── neden sabitleri ─────────────────────────────────────────────────────────
def test_log_neden_sabitleri_tanimli():
    assert vc.LOG_NEDEN_BOS_YANIT
    assert vc.LOG_NEDEN_AZ_BAR
    assert vc.LOG_NEDEN_SEMBOL
