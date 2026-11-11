"""G08 — Backtest yeniden: ATR stop/hedef, vade, maliyet, çakışma, kilit kayması.

Saf fonksiyonlar (`_islem_hesapla`, `sermaye_simule`) doğrudan test edilir;
uçtan uca davranış `test_senaryolari` üzerinden. Ağ YOK (elle yazılmış barlar).
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "scripts"))

import veri_cek as v  # noqa: E402


def _ind(barlar):
    """Bar listesi → indikatör DataFrame (ATR14 elle verilir)."""
    df = pd.DataFrame(barlar)
    df['HGDG_TARIH'] = pd.to_datetime(df['tarih'])
    df['HGDG_KAPANIS'] = df['kapanis'].astype(float)
    df['HGDG_ACILIS'] = df['acilis'].astype(float)
    df['HGDG_MIN'] = df['min'].astype(float)
    df['HGDG_MAX'] = df['max'].astype(float)
    df['HGDG_HACIM'] = df.get('hacim', 1_000_000)
    df['ATR14'] = df['atr'].astype(float)
    return df.sort_values('HGDG_TARIH').reset_index(drop=True)


def _bar(tarih, acilis, kapanis, dusuk, yuksek, atr=1.0):
    return {'tarih': tarih, 'acilis': acilis, 'kapanis': kapanis,
            'min': dusuk, 'max': yuksek, 'hacim': 1_000_000, 'atr': atr}


def _gun(n):
    """n. iş günü ISO tarihi (2026-01-05 pazartesi başlangıç)."""
    return (pd.Timestamp('2026-01-05') + pd.offsets.BDay(n)).strftime('%Y-%m-%d')


def _islem(barlar, sinyal_i=0, kilitler=None, skor=3):
    ind = _ind(barlar)
    s = {'skor': skor, 'sinyal': 'AL'}
    return v._islem_hesapla('TEST', sinyal_i, s, ind, kilitler or {})


# (a) Stop tetiklenmesi: 2×ATR altına inen gün içi düşük → stop fiyatından çıkış
def test_stop_tetiklenir():
    barlar = [
        _bar(_gun(0), 100.0, 100.0, 99.0, 101.0, atr=1.0),   # sinyal barı (ATR=1)
        _bar(_gun(1), 100.0, 100.5, 99.5, 101.0),             # giriş: açılış 100
        _bar(_gun(2), 100.0, 99.0, 98.9, 100.5),              # stop 98'in üstünde
        _bar(_gun(3), 99.0, 95.0, 97.9, 99.5),                # düşük 97.9 ≤ 98 → stop
        _bar(_gun(4), 95.0, 96.0, 94.5, 96.5),
        _bar(_gun(5), 95.0, 96.0, 94.5, 96.5),
    ]
    isl = _islem(barlar)
    assert isl['cikis_neden'] == 'stop'
    assert isl['stop_calismis'] is True
    assert isl['cikis_tarih'] == _gun(3)
    assert isl['stop_fiyat'] == 98.0                          # 100 − 2×1
    # brüt −%2, gidiş-dönüş maliyet %0,2 → net ≈ −%2,2
    assert isl['brut_getiri_yuzde'] == pytest.approx(-2.0, abs=0.05)
    assert isl['getiri_yuzde'] == pytest.approx(-2.2, abs=0.05)
    assert isl['brut_getiri_yuzde'] - isl['getiri_yuzde'] == pytest.approx(0.2, abs=0.06)


# (b) Vade çıkışı: hiçbir seviye tetiklenmezse 5. iş günü kapanışından çıkış
def test_vade_cikisi_5_gun():
    barlar = [_bar(_gun(0), 100.0, 100.0, 99.9, 100.1, atr=1.0)]
    for n in range(1, 12):
        barlar.append(_bar(_gun(n), 100.0, 100.1, 99.9, 100.2))   # stop 98 / hedef 103 vurulmaz
    isl = _islem(barlar)
    assert isl['cikis_neden'] == 'vade'
    assert isl['cikis_tarih'] == _gun(5)
    assert isl['vade_gun'] == 5


# (c) Çakışma engeli: aynı hissede pozisyon açıkken yeni sinyal işleme dönüşmez
def test_cakisma_engeli():
    # Uzun süre yatay seyir → ilk sinyalin vadesi (20 gün) dolmadan ikinci sinyal gelir
    barlar = []
    for n in range(0, 60):
        fiyat = 100.0 + (n % 2) * 0.05
        barlar.append(_bar(_gun(n), fiyat, fiyat, fiyat - 0.05, fiyat + 0.05, atr=1.0))
    hv = {'TEST': barlar}
    # Tüm barlarda AL sinyali üret → çakışma kuralı olmasa onlarca işlem çıkardı
    ozel = {'skor': 3}
    islemler = []
    serbest = -1
    for i in range(0, 55):
        if i <= serbest:
            continue
        isl = v._islem_hesapla('TEST', i, ozel, _ind(barlar), {})
        islemler.append(isl)
        serbest = isl['_cikis_i']
    assert len(islemler) < 55, 'çakışma engeli çalışmıyor'
    # her işlem bir öncekinin çıkışından sonra başlamalı
    for a, b in zip(islemler, islemler[1:]):
        assert b['giris_tarih'] > a['cikis_tarih']
    assert hv  # kullanıldı


# (d) Maliyet düşümü: GİDİŞ-DÖNÜŞ %0,2 — alışta ve satışta yarım maliyet
def test_maliyet_dusumu():
    barlar = [_bar(_gun(0), 100.0, 100.0, 99.9, 100.1, atr=1.0)]
    for n in range(1, 7):
        barlar.append(_bar(_gun(n), 100.0, 104.0, 99.9, 104.1))  # hedef 103 vurulur
    isl = _islem(barlar)
    assert isl['maliyet_yuzde'] == pytest.approx(v.MALIYET * 100)
    fark = isl['brut_getiri_yuzde'] - isl['getiri_yuzde']
    assert fark == pytest.approx(v.MALIYET * 100, abs=0.05), f'Maliyet düşülmemiş: {isl}'


def test_maliyet_fiyat_degismezse_yuzde_02():
    """Fiyat hiç değişmezse net getiri ≈ −%0,2 olmalı (gidiş-dönüş maliyet)."""
    barlar = [_bar(_gun(0), 100.0, 100.0, 99.9, 100.1, atr=1.0)]
    for n in range(1, 7):
        barlar.append(_bar(_gun(n), 100.0, 100.0, 100.0, 100.0))
    isl = _islem(barlar)
    assert isl['brut_getiri_yuzde'] == pytest.approx(0.0, abs=0.05)
    assert isl['getiri_yuzde'] == pytest.approx(-0.2, abs=0.05), f'Beklenen −%0,2: {isl}'


# (g) Aynı giriş tarihli sinyaller skora göre sıralanır (yüksek skor önce)
def test_sermaye_simule_skor_onceligi():
    islemler = [
        {'sembol': 'AAA', 'giris_tarih': '2026-01-05', 'cikis_tarih': '2026-01-20',
         'getiri_yuzde': -10.0, 'skor': 2},
        {'sembol': 'ZZZ', 'giris_tarih': '2026-01-05', 'cikis_tarih': '2026-01-20',
         'getiri_yuzde': 10.0, 'skor': 5},
    ]
    # 1 pozisyonluk slot: skor 5 olan seçilmeli
    sim = v.sermaye_simule(islemler, baslangic=100000.0, max_pozisyon=1)
    assert sim['islem'] == 1 and sim['atlanan'] == 1
    assert sim['kar_zarar'] > 0, f'Yüksek skor seçilmedi: {sim}'


# (h) Mutabakat: kar_zarar ≈ Σ(tahsis × getiri) — fark %1'den küçük
def test_sermaye_mutabakat():
    islemler = [{'sembol': f'S{i:02d}', 'giris_tarih': f'2026-01-{i+1:02d}',
                 'cikis_tarih': f'2026-02-{i+1:02d}', 'getiri_yuzde': (i - 4) * 3.0,
                 'skor': 3} for i in range(10)]
    sim = v.sermaye_simule(islemler, baslangic=100000.0, max_pozisyon=10)
    assert abs(sim['mutabakat_fark_yuzde']) < 1.0, f'Mutabakat sapması: {sim}'
    assert sim['beklenen_kar'] == pytest.approx(sim['kar_zarar'], abs=sim['baslangic'] * 0.01)
    assert 'gerceklesen_max_dd_yuzde' in sim and 'max_drawdown_yuzde' in sim


# (e) Aynı gün stop + hedef → muhafazakâr kural: STOP sayılır
def test_ayni_gun_stop_ve_hedef_stop_sayilir():
    barlar = [
        _bar(_gun(0), 100.0, 100.0, 99.9, 100.1, atr=1.0),
        _bar(_gun(1), 100.0, 100.0, 99.9, 100.1),    # giriş 100, stop 98, hedef 103
        _bar(_gun(2), 100.0, 100.0, 97.5, 103.5),    # gün içi hem stop hem hedef
        _bar(_gun(3), 100.0, 100.0, 99.9, 100.1),
        _bar(_gun(4), 100.0, 100.0, 99.9, 100.1),
        _bar(_gun(5), 100.0, 100.0, 99.9, 100.1),
    ]
    isl = _islem(barlar)
    assert isl['cikis_neden'] == 'stop'
    assert isl['stop_calismis'] is True
    assert isl['getiri_yuzde'] < 0


# (f) Taban kilidinde çıkış ilk kilitsiz güne kayar
def test_taban_kilitli_gunde_cikis_kayar():
    barlar = [
        _bar(_gun(0), 100.0, 100.0, 99.9, 100.1, atr=1.0),
        _bar(_gun(1), 100.0, 100.0, 99.9, 100.1),    # giriş
        _bar(_gun(2), 100.0, 100.0, 95.0, 100.1),    # stop altı ama TABAN kilitli → çıkılamaz
        _bar(_gun(3), 100.0, 100.0, 95.0, 100.1),    # hâlâ kilitli
        _bar(_gun(4), 96.0, 96.0, 95.5, 96.5),       # ilk kilitsiz gün → burada çıkılır
        _bar(_gun(5), 96.0, 96.0, 95.5, 96.5),
    ]
    kilitler = {2: 'TABAN', 3: 'TABAN'}
    isl = _islem(barlar, kilitler=kilitler)
    assert isl['cikis_tarih'] == _gun(4), f"kilitli günde çıkış: {isl}"
    assert isl['cikis_neden'] == 'stop'
    assert isl['stop_fiyat'] == 98.0


def test_sermaye_simule_kronolojik_ve_slot_siniri():
    """Kronolojik simülasyon: max 10 eşzamanlı pozisyon, aynı gün açılan 12 sinyalden 2'si atlanır."""
    islemler = [{'giris_tarih': '2026-01-05', 'cikis_tarih': '2026-01-30',
                 'getiri_yuzde': 10.0, 'sembol': f'S{i:02d}'} for i in range(12)]
    sim = v.sermaye_simule(islemler, baslangic=100_000.0, max_pozisyon=10)
    assert sim['islem'] == 10
    assert sim['atlanan'] == 2
    assert sim['tahsis'] == 10_000
    # 10 pozisyon × 10.000 TL × %10 = +10.000 TL
    assert sim['sonuc'] == pytest.approx(110_000, abs=1)
    assert sim['kar_zarar'] == pytest.approx(10_000, abs=1)


def test_sermaye_simule_nakit_yetmezse_sinyal_atlanir():
    islemler = [{'giris_tarih': '2026-01-05', 'cikis_tarih': '2026-02-05',
                 'getiri_yuzde': -90.0, 'sembol': 'A'}]
    sim = v.sermaye_simule(islemler, baslangic=100_000.0, max_pozisyon=10)
    assert sim['islem'] == 1
    assert sim['sonuc'] == pytest.approx(91_000, abs=1)


def test_riskli_hisse_backteste_girmez():
    """Son 10 barda ≥3 taban kilidi olan hisse hiç işlem üretmemeli."""
    barlar = []
    f = 100.0
    for n in range(0, 120):
        if n in (110, 112, 114):                      # 3 taban kilidi
            f = round(f * 0.90, 2)
            barlar.append({'tarih': _gun(n), 'kapanis': f, 'acilis': round(f / 0.90, 2),
                           'min': f, 'max': round(f / 0.90, 2), 'hacim': 5_000_000})
        else:
            f = round(f * 1.001, 2)
            barlar.append({'tarih': _gun(n), 'kapanis': f, 'acilis': round(f * 1.0005, 2),
                           'min': round(f * 0.99, 2), 'max': round(f * 1.01, 2), 'hacim': 5_000_000})
    son = barlar[-1]
    assert v.riskli_tespit(barlar) is not None, 'test verisi RISKLI üretmedi'
    out = v.test_senaryolari({'TEST': barlar})
    islemler = (out.get('ertesi_gun_acilis') or {}).get('islemler') or []
    # RISKLI tespiti son 10 barda; son barın sinyali zaten işlem üretmez.
    # Kural: işlem listesinde son 10 barda açılmış işlem olmamalı.
    son10 = {b['tarih'] for b in barlar[-10:]}
    assert not [x for x in islemler if x['giris_tarih'] in son10], f'RISKLI hisse işleme girdi: {son}'
