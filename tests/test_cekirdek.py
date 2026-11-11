"""Ağ bağlantısız çekirdek testler — `python -m pytest tests -q`"""
import json, sys, datetime as dt
from pathlib import Path
import numpy as np, pandas as pd

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / 'scripts'))
import veri_cek as vc                       # noqa: E402
import indikatorler as ind                 # noqa: E402


def sentetik(n=260, egim=0.002, tohum=1):
    r = np.random.default_rng(tohum)
    c = 100 * np.exp(np.cumsum(egim + r.normal(0, 0.01, n)))
    tarih = pd.bdate_range('2025-10-01', periods=n)
    return pd.DataFrame({'HGDG_TARIH': tarih, 'HGDG_KAPANIS': c, 'HGDG_MAX': c * 1.01,
                         'HGDG_MIN': c * 0.99, 'HGDG_HACIM': r.integers(1e5, 2e5, n).astype(float)})


def test_yukari_trend_artik_mumkun():
    son = ind.tum_indikatorler(sentetik(260, egim=0.004)).iloc[-1]
    s = ind.sinyal_hesapla(son)
    assert s['trend'] == 'YUKARI' and s['trend_kaynak'] == 'SMA50/200'


def test_sma200_yoksa_kisa_trend():
    son = ind.tum_indikatorler(sentetik(125, egim=0.004)).iloc[-1]
    s = ind.sinyal_hesapla(son)
    assert s['trend'] == 'YUKARI' and 'kısa' in s['trend_kaynak']


def test_obv_egim_hesaplaniyor():
    out = ind.tum_indikatorler(sentetik(120))
    assert out['OBV_EGIM'].notna().sum() > 50


def test_duygu_alt_dize_hatasi_yok():
    assert vc._yon_etiket('TCMB faiz kararı açıklandı')[0] == 'notr'          # 'karar' ≠ 'kar'
    assert vc._yon_etiket('AK Partisi grup toplantısı yapıldı')[0] == 'notr'   # 'partisi' ≠ 'artış'
    assert vc._yon_etiket('Şirketin net kârı rekor kırdı')[0] == 'pozitif'
    assert vc._yon_etiket('Fed faiz artışı sinyali verdi')[0] == 'negatif'
    assert vc._yon_etiket('Merkez bankası faiz indirdi')[0] == 'pozitif'
    assert vc._yon_etiket('Holding konkordato ilan etti')[0] == 'negatif'


def test_tam_kesit_log_gunu_uzerine_yazar(tmp_path, monkeypatch):
    monkeypatch.setattr(vc, 'DATA_DIR', tmp_path)
    satir = lambda f: [{'sembol': 'AAA', 'tarih': '2026-11-10', 'fiyat': f, 'skor': 1}]
    vc.tam_kesit_log(satir(10.0), {'deger': 1, 'tarih': '2026-11-10'}, 'test')
    vc.tam_kesit_log(satir(10.5), {'deger': 1, 'tarih': '2026-11-10'}, 'test')   # gün içi 2. çalışma
    satirlar = (tmp_path / 'log' / '2026-11.jsonl').read_text().splitlines()
    assert len(satirlar) == 1 and json.loads(satirlar[0])['rows'][0]['fiyat'] == 10.5


def test_utc_damga():
    assert dt.datetime.fromisoformat(vc.utc_now_iso()).tzinfo is not None
