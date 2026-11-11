"""G05 — sinyalleri_hesapla entegrasyonu (filtre yolu). Ağ YOK, indikatör monkeypatch'li."""
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "scripts"))

import indikatorler  # noqa: E402
import veri_cek  # noqa: E402


@pytest.fixture
def al_sinyali(monkeypatch):
    """Tüm hisselere AL ürettir — filtre (likidite/riskli) yolunu izole test eder."""
    gercek = indikatorler.sinyal_hesapla

    def fake(row):
        s = dict(gercek(row))
        s['sinyal'] = 'AL'
        s['skor'] = 5
        return s

    monkeypatch.setattr(indikatorler, "sinyal_hesapla", fake)
    return fake


def _seri(hacim=5_000_000, taban_say=0, n=70):
    rows = []
    for i in range(n):
        f = 100 + i * 0.1
        rows.append({'tarih': f'2026-{8 + (i // 28):02d}-{(i % 28) + 1:02d}',
                     'acilis': f, 'max': f + 1, 'min': f - 1, 'kapanis': f, 'hacim': hacim})
    for k in range(taban_say):
        onc = rows[-1]['kapanis']
        f = round(onc * 0.90, 2)
        rows.append({'tarih': f'2026-11-{k + 20:02d}', 'acilis': onc, 'max': onc,
                     'min': f, 'kapanis': f, 'hacim': 1_000_000})
    return rows


def test_filtre_likidite_al_izleye_duser(al_sinyali):
    r = veri_cek.sinyalleri_hesapla({'DUSUK': _seri(hacim=100_000)}, {})
    assert not [x for x in r['al'] if x['sembol'] == 'DUSUK']
    izle = [x for x in r['izle'] if x['sembol'] == 'DUSUK']
    assert izle and izle[0]['filtre'] == 'likidite eşiği altı'
    assert izle[0]['sinyal_ham'] == 'AL'


def test_filtre_sorunlu_hisse_riskye_duser(al_sinyali):
    r = veri_cek.sinyalleri_hesapla({'SORUNLU': _seri(taban_say=3)}, {})
    risk = [x for x in r['riskli'] if x['sembol'] == 'SORUNLU']
    assert risk and 'taban' in risk[0]['filtre']
    assert not [x for x in r['al'] if x['sembol'] == 'SORUNLU']


def test_filtre_temiz_hisse_al_kalir(al_sinyali):
    r = veri_cek.sinyalleri_hesapla({'TEMIZ': _seri()}, {})
    assert [x['sembol'] for x in r['al']] == ['TEMIZ']


def test_filtre_riskli_once_gelir_likiditeden(al_sinyali):
    """Hem düşük likidite hem 3 taban → RISKLI kazanır (md.6 > md.2)."""
    r = veri_cek.sinyalleri_hesapla({'HER_IKISI': _seri(hacim=100_000, taban_say=3)}, {})
    assert [x['sembol'] for x in r['riskli']] == ['HER_IKISI']
    assert not r['izle']


def test_filtre_skor_istatistigi_haric(al_sinyali):
    """Yeni arz + riskli hisseler skor istatistiğinden hariç tutulur (md.4)."""
    veri = {'TEMIZ': _seri(), 'ARZ': _seri(), 'SORUNLU': _seri(taban_say=3)}
    r = veri_cek.sinyalleri_hesapla(veri, {'ARZ': '2026-10-01'})
    st = r['skor_istatistik']
    assert st['kapsam'] == 1          # yalnız TEMIZ
    assert st['haric'] == 2           # ARZ + SORUNLU
    assert st['ort_skor'] == 5.0


def test_cikti_alanlari_mevcut():
    r = veri_cek.sinyalleri_hesapla({'A': _seri()}, {})
    for alan in ('durum', 'al', 'tut', 'sat', 'izle', 'riskli', 'filtre_esikleri',
                 'skor_istatistik', 'toplam'):
        assert alan in r
    kayit = r['_tum'][0]
    for alan in ('kilit', 'likidite_tl', 'ipo_yeni', 'tedbir', 'riskli', 'taban_10g', 'durum'):
        assert alan in kayit


def test_ipo_bayragi_kayda_yazilir():
    r = veri_cek.sinyalleri_hesapla({'ARZ': _seri()}, {'ARZ': '2026-10-01'})
    kayit = r['_tum'][0]
    assert kayit['ipo_yeni'] is True
    assert kayit['ipo_tarih'] == '2026-10-01'


def test_tedbir_kaynak_yoksa_none():
    r = veri_cek.sinyalleri_hesapla({'A': _seri()}, {})
    assert r['_tum'][0]['tedbir'] is None
