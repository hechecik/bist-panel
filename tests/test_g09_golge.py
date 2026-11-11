"""G09 — gölge mod teknik eklemeler. Ağ YOK, tamamen sentetik veri.

Kapsam: saf göstergeler (rs_degisim, hacim_orani, vol20, zirve_uzak, trend_atr),
golge_gostergeler sarmalayıcısı, genislik_hesapla ve skor/sinyal dokunulmazlığı.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "scripts"))

import indikatorler  # noqa: E402
import veri_cek  # noqa: E402


# ── yardımcılar ───────────────────────────────────────────────

def _seri(degerler):
    return pd.Series([float(x) for x in degerler])


def _df(kapanis, hacim=None, n=None):
    """golge_gostergeler'ın beklediği HGDG_* kolonlu df."""
    kapanis = [float(x) for x in kapanis]
    n = n or len(kapanis)
    hacim = hacim if hacim is not None else [1_000_000.0] * n
    return pd.DataFrame({
        'HGDG_TARIH': pd.date_range('2025-01-01', periods=n, freq='D'),
        'HGDG_KAPANIS': kapanis,
        'HGDG_HACIM': [float(x) for x in hacim],
        'HGDG_MIN': [x * 0.99 for x in kapanis],
        'HGDG_MAX': [x * 1.01 for x in kapanis],
    })


# ── rs_degisim / RS20 / RS60 ──────────────────────────────────

def test_rs_degisim_oransal_degisim_dogru():
    # hisse 100→110 (%+10), endeks 300 (sabit) ⇒ RS20 = +10%
    hisse = _seri([100.0] * 20 + [110.0])   # 21 bar, 20 gün önce = 100
    endeks = _seri([300.0] * 21)
    assert indikatorler.rs_degisim(hisse, endeks, 20) == pytest.approx(10.0)


def test_rs_degisim_endeks_de_yukselirse_goreli_duser():
    # hisse %+10, endeks %+20 ⇒ RS20 = (1.10/1.20 - 1)*100 ≈ -8.33
    hisse = _seri([100.0] * 20 + [110.0])
    endeks = _seri([100.0] * 20 + [120.0])
    assert indikatorler.rs_degisim(hisse, endeks, 20) == pytest.approx(-8.33, abs=0.01)


def test_rs_degisim_yetersiz_bar_none():
    assert indikatorler.rs_degisim(_seri(range(10)), _seri(range(10)), 20) is None


def test_rs_degisim_sifir_endeks_none():
    hisse = _seri([10.0] * 25)
    endeks = _seri([0.0] * 25)              # sıfıra bölme → NaN → None
    assert indikatorler.rs_degisim(hisse, endeks, 20) is None


def test_rs_serisi_sonsuz_deger_temizlenir():
    oran = indikatorler.rs_serisi(_seri([10.0, 20.0]), _seri([0.0, 10.0]))
    assert oran.isna().tolist() == [True, False]
    assert oran.iloc[1] == pytest.approx(2.0)


# ── hacim_orani ───────────────────────────────────────────────

def test_hacim_orani_medyana_gore():
    # son 20 gün 1.0M, bugün 2.0M ⇒ 2.0×
    hacim = [1_000_000.0] * 20 + [2_000_000.0]
    assert indikatorler.hacim_orani(pd.Series(hacim)) == pytest.approx(2.0)


def test_hacim_orani_medyan_aykiri_degerden_etkilenmez():
    # bir gün 100M (aykırı) — medyan hâlâ 1M ⇒ oran 1.0×
    hacim = [1_000_000.0] * 20 + [100_000_000.0, 1_000_000.0]
    assert indikatorler.hacim_orani(pd.Series(hacim)) == pytest.approx(1.0)


def test_hacim_orani_yetersiz_bar_none():
    assert indikatorler.hacim_orani(pd.Series([1.0] * 10)) is None


# ── vol20 ─────────────────────────────────────────────────────

def test_vol20_sabit_seride_sifir():
    assert indikatorler.vol20(_seri([100.0] * 25)) == pytest.approx(0.0)


def test_vol20_oynak_seride_pozitif():
    v = indikatorler.vol20(_seri([100, 110, 100, 110, 100, 110, 100, 110, 100, 110,
                                  100, 110, 100, 110, 100, 110, 100, 110, 100, 110, 100]))
    assert v is not None and v > 5


def test_vol20_yetersiz_bar_none():
    assert indikatorler.vol20(_seri([100.0] * 5)) is None


# ── zirve_uzak ────────────────────────────────────────────────

def test_zirve_uzak_zirvede_sifir():
    assert indikatorler.zirve_uzak(_seri([100.0] * 10 + [200.0])) == pytest.approx(0.0)


def test_zirve_uzak_zirveden_uzak_negatif():
    # zirve 200, son 150 ⇒ (150/200 - 1)*100 = -25
    assert indikatorler.zirve_uzak(_seri([100.0, 200.0, 150.0])) == pytest.approx(-25.0)


def test_zirve_uzak_bos_seri_none():
    assert indikatorler.zirve_uzak(pd.Series([], dtype=float)) is None


# ── trend_atr ─────────────────────────────────────────────────

def test_trend_atr_hesabi():
    # (110 - 105) / 2.5 = 2.0
    v = indikatorler.trend_atr(_seri([100.0, 110.0]), _seri([100.0, 105.0]), _seri([1.0, 2.5]))
    assert v == pytest.approx(2.0)


def test_trend_atr_sma_altinda_negatif():
    v = indikatorler.trend_atr(_seri([100.0, 95.0]), _seri([100.0, 100.0]), _seri([1.0, 2.5]))
    assert v == pytest.approx(-2.0)


def test_trend_atr_sifir_atr_none():
    assert indikatorler.trend_atr(_seri([100.0]), _seri([100.0]), _seri([0.0])) is None


def test_trend_atr_nan_atr_none():
    assert indikatorler.trend_atr(_seri([100.0]), _seri([100.0]), _seri([np.nan])) is None


# ── golge_gostergeler (sarmalayıcı) ───────────────────────────

def test_golge_gostergeler_tum_alanlar_doner():
    kapanis = [100.0 + i for i in range(300)]
    hacim = [1_000_000.0] * 299 + [2_000_000.0]
    df = _df(kapanis, hacim)
    endeks = {'seri': [['2025-01-01', 100.0], ['2025-10-27', 300.0]]}

    c = df.set_index('HGDG_TARIH')['HGDG_KAPANIS']
    e = pd.Series([x[1] for x in endeks['seri']],
                  index=pd.to_datetime([x[0] for x in endeks['seri']]))
    g = veri_cek.golge_gostergeler(df, {'seri': [[d.strftime('%Y-%m-%d'), float(v)]
                                                 for d, v in e.items()]})

    assert set(g) == {'RS20', 'RS60', 'HACIM_ORAN', 'VOL20', 'ZIRVE_UZAK', 'TREND_ATR'}
    assert g['HACIM_ORAN'] == pytest.approx(2.0)
    assert g['VOL20'] is not None
    assert g['ZIRVE_UZAK'] == pytest.approx(0.0)


def test_golge_gostergeler_endeks_yoksa_rs_none():
    df = _df([100.0 + i for i in range(300)])
    g = veri_cek.golge_gostergeler(df, None)
    assert g['RS20'] is None and g['RS60'] is None
    assert g['HACIM_ORAN'] is not None


def test_golge_gostergeler_bos_df_cokmez():
    g = veri_cek.golge_gostergeler(_df([100.0] * 3), None)
    assert g['HACIM_ORAN'] is None and g['ZIRVE_UZAK'] is not None


# ── genislik_hesapla ──────────────────────────────────────────

def _hisse(kapanis):
    return pd.DataFrame({'HGDG_TARIH': pd.date_range('2024-01-01', periods=len(kapanis), freq='D'),
                         'HGDG_KAPANIS': [float(x) for x in kapanis]})


def test_genislik_sayim_dogru():
    seriler = {
        'A': _hisse([100.0] * 300 + [120.0]),        # MA50 üstü, yükselen, 52h zirve
        'B': _hisse([100.0] * 300 + [80.0]),         # MA50 altı, düşen
        'C': _hisse([120.0] * 300 + [100.0]),        # MA50 altı, düşen, zirveden uzak
    }
    g = indikatorler.genislik_hesapla(seriler)
    assert g['hisse'] == 3
    assert g['yukselen'] == 1
    assert g['ma50_ustu_yuzde'] == pytest.approx(33.3, abs=0.1)
    assert g['dusen'] == 2
    assert g['yeni_zirve_52h'] == 1


def test_genislik_kisa_gecmis_52h_hesaplanmaz():
    seriler = {'A': _hisse([100.0] * 60 + [200.0])}   # 252 bar yok
    g = indikatorler.genislik_hesapla(seriler)
    assert g['yeni_zirve_52h'] == 0
    assert g['yeni_dip_52h'] == 0
    assert g['hisse'] == 1


def test_genislik_bos_veri_yok_durumu():
    assert indikatorler.genislik_hesapla({}) == {'durum': 'veri yok'}
    assert indikatorler.genislik_hesapla(None) == {'durum': 'veri yok'}


def test_genislik_bozuk_hisse_atlanir():
    seriler = {'A': _hisse([100.0] * 60), 'BOZUK': None, 'KISA': _hisse([100.0])}
    g = indikatorler.genislik_hesapla(seriler)
    assert g['hisse'] == 1


# ── gölge mod garantisi: skor/sinyal dokunulmaz ───────────────

def test_golge_alanlari_skor_ve_sinyali_degistirmez():
    """golge_gostergeler çıktısı sinyal/skor anahtarı içermez → sinyale sızamaz."""
    df = _df([100.0 + i for i in range(300)])
    g = veri_cek.golge_gostergeler(df, None)
    assert 'skor' not in g and 'sinyal' not in g
    assert not any(k in g for k in ('stop', 'hedef', 's1', 'r1'))


def test_sinyalleri_hesapla_endeks_parametresi_geriye_uyumlu():
    """endeks parametresi opsiyonel olmalı — eski imza ile çağrı bozulmasın."""
    import inspect
    imza = inspect.signature(veri_cek.sinyalleri_hesapla)
    pars = list(imza.parameters)
    assert 'endeks' in pars
    assert imza.parameters['endeks'].default is None
