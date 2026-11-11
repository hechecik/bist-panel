"""G02 — bedelsiz bölünme (split) düzeltmesi testleri.

Ağ bağlantısı yok: `python3 -m pytest tests -q`

Sentetik seri mantığı: `seri()` HAM (düzeltilmemiş) seriyi üretir — bozuk bir
veri sağlayıcısının verdiği gibi, bölünme gününde fiyat aniden 1/oran'a düşer.
`gercek_seri()` ise aynı fiyatların DOĞRU (bölünmüş, tek ölçekli) halini üretir;
düzeltmenin başarısı bu iki serinin örtüşmesiyle ölçülür.
"""
import sys
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / 'scripts'))
import veri_cek as vc                       # noqa: E402


def _bar(tarih, k, hacim):
    """Tek OHLCV bar. Açılış = kapanış (gap yok) → oran tam olarak 1/oran çıkar."""
    return {
        'tarih': tarih,
        'acilis': round(float(k), 4),
        'kapanis': round(float(k), 4),
        'min': round(float(k) * 0.99, 4),
        'max': round(float(k) * 1.01, 4),
        'hacim': int(hacim),
    }


def gercek_seri(fiyatlar, hacimler=None):
    """Bölünmüş (doğru, tek ölçekli) seri — n=len(fiyatlar).

    Açılış = önceki kapanış (gap yok); böylece fiyat oranı = açılış oranı olur ve
    sentetik seri, gerçek bir bölünme dışında yanlış pozitif üretmez.
    """
    tarih = pd.bdate_range('2025-01-02', periods=len(fiyatlar)).date
    hacimler = hacimler or [1_000_000.0] * len(fiyatlar)
    rows = []
    for i, k in enumerate(fiyatlar):
        k = float(k)
        rows.append(_bar(str(tarih[i]), k, hacimler[i]))
    return rows


def seri(fiyatlar, hacimler=None, bolunme_gunu=None, oran=1.0):
    """HAM (düzeltilmemiş) OHLCV serisi — bölünme gününde fiyat `oran` ile çarpılır.

    Gerçek borsada bedelsiz bölünmede fiyat `oran` kadar düşer (1:20 → 0.05) ve
    hacim `1/oran` katına çıkar; bölünme gününün açılışı `önceki kapanış × oran`dır.
    Düzeltilmemiş feed'de bu, −%95'lik bir sıçrama gibi görünür.
    """
    tarih = pd.bdate_range('2025-01-02', periods=len(fiyatlar))
    hacimler = hacimler or [1_000_000.0] * len(fiyatlar)
    rows = []
    for i in range(len(fiyatlar)):
        k = float(fiyatlar[i])
        h = float(hacimler[i])
        bolundu = bolunme_gunu is not None and i >= bolunme_gunu
        if bolundu:
            k *= oran
            h /= oran
        b = _bar(str(tarih[i].date()), k, h)
        if bolunme_gunu is not None and i == bolunme_gunu:
            # Bölünme günü açılışı = önceki kapanış × oran (gap yok) → oran tam çıkar
            b['acilis'] = round(float(fiyatlar[i - 1]) * oran, 4)
            b['min'] = round(b['acilis'] * 0.99, 4)
            b['max'] = round(b['acilis'] * 1.01, 4)
        rows.append(b)
    return rows


def max_gunluk_dusus(rows):
    """Serideki en büyük günlük kapanış düşüşü (negatif yüzde, ör. -95.0)."""
    en_kotu = 0.0
    for i in range(1, len(rows)):
        onceki = rows[i - 1]['kapanis']
        if onceki and onceki > 0:
            en_kotu = min(en_kotu, rows[i]['kapanis'] / onceki - 1.0)
    return en_kotu * 100


def test_1e20_bolunme_duzeltilir():
    """Kabul kriteri: sentetik 1:20 bölünme → düzeltme sonrası maks. günlük düşüş < %11."""
    fiyatlar = [100.0 + 0.3 * i for i in range(120)]
    ham = seri(fiyatlar, bolunme_gunu=90, oran=0.05)
    # Gerçek (doğru) seri bölünme SONRASI ölçekte: 1:20 → eski fiyatlar ÷20
    dogru = gercek_seri([100.0 + 0.3 * i for i in range(120)])

    # Düzeltme ÖNCESİ: bölünme gününde ~-%95 sıçrama
    assert max_gunluk_dusus(ham) < -90, "sentetik seride bölünme sıçraması oluşmadı"

    tespit = vc.bolunme_tespit(ham)
    assert len(tespit) == 1, f"tek bölünme beklenirdi, {len(tespit)} bulundu"
    assert tespit[0]['tarih'] == ham[90]['tarih']
    assert abs(tespit[0]['oran'] - 0.05) < 1e-6, "oran = bugünkü açılış / önceki kapanış olmalı"

    duzeltilmis = vc.bolunme_duzelt(ham, tespit)

    # Düzeltme SONRASI: en büyük günlük düşüş %11'den küçük olmalı (kabul kriteri)
    md = max_gunluk_dusus(duzeltilmis)
    assert md > -11.0, f"düzeltme sonrası düşüş hâlâ %{abs(md):.1f}"

    # Ve seri, tek ölçekli gerçek seriyle birebir örtüşmeli (tüm barlar)
    for i in range(len(ham)):
        assert abs(duzeltilmis[i]['kapanis'] - dogru[i]['kapanis'] * 0.05) < 1e-3, f"bar {i} ölçek hatası"


def test_duzeltme_oncesi_barlari_olceklendirir():
    """OHLC ÷ oran, hacim × oran; bölünme günü ve sonrası değişmez; girdi korunur."""
    ham = seri([200.0] * 60, bolunme_gunu=40, oran=0.05)
    duzeltilmis = vc.bolunme_duzelt(ham, vc.bolunme_tespit(ham))

    # bölünme öncesi bar: 200 × 0.05 = 10 (bölünme sonrası ölçek)
    assert abs(duzeltilmis[0]['kapanis'] - 10.0) < 1e-6
    assert abs(duzeltilmis[0]['hacim'] - 1_000_000 / 0.05) <= 1
    # bölünme günü ve sonrası dokunulmamış (200 × 0.05 = 10)
    assert abs(duzeltilmis[40]['kapanis'] - 10.0) < 1e-6
    assert duzeltilmis[-1]['hacim'] == ham[-1]['hacim']
    # saf fonksiyon: girdi değişmemeli
    assert abs(ham[0]['kapanis'] - 200.0) < 1e-9


def test_yuzde10_ile_30_arasi_dususlere_dokunulmaz():
    """BIST marjı ±%10; −%10 ile −%30 arası düşüş gerçek olabilir → düzeltme yapılmamalı."""
    for dusus in (0.10, 0.15, 0.25, 0.29):
        fiyatlar = [100.0] * 20
        fiyatlar[10] = 100.0 * (1 - dusus)
        fiyatlar[11] = fiyatlar[10]            # geri sıçramasın
        rows = gercek_seri(fiyatlar)
        assert vc.bolunme_tespit(rows) == [], f"-%{dusus*100:.0f} gerçek düşüş bölünme sayıldı"
        assert vc.bolunme_duzelt(rows, []) is rows


def test_esik_altindaki_dusus_bolunme_sayilir():
    """-%30'dan büyük düşüş fiziksel olarak imkânsız → bölünme kabul edilir."""
    fiyatlar = [100.0] * 20
    fiyatlar[10] = 40.0        # −%60: BIST marjıyla imkânsız → bölünme
    fiyatlar[11] = 40.0
    rows = gercek_seri(fiyatlar)
    rows[10]['acilis'] = 40.0  # bölünme günü açılışı = önceki kapanış × oran (gap yok)
    tespit = vc.bolunme_tespit(rows)
    assert len(tespit) == 1
    assert abs(tespit[0]['oran'] - 0.4) < 1e-3


def test_bolunme_uygula_saglik_listesi_uretir():
    """bolunme_uygula: {sembol: [{tarih, oran}]} döner, seriyi yerinde düzeltir."""
    fiyatlar = [500.0 + i for i in range(80)]
    hisse_veri = {
        'SPLIT': seri(fiyatlar, bolunme_gunu=60, oran=0.05),
        'DUZ': gercek_seri([50.0 + 0.1 * i for i in range(80)]),
    }
    duzeltmeler = vc.bolunme_uygula(hisse_veri)

    assert 'SPLIT' in duzeltmeler and 'DUZ' not in duzeltmeler
    t = duzeltmeler['SPLIT'][0]
    assert set(t) == {'tarih', 'oran'}
    assert abs(t['oran'] - 0.05) < 1e-6
    assert max_gunluk_dusus(hisse_veri['SPLIT']) > -11.0


def test_bolunme_yoksa_seri_aynen_doner():
    rows = gercek_seri([100.0 + 0.5 * i for i in range(50)])
    assert vc.bolunme_tespit(rows) == []
    assert vc.bolunme_duzelt(rows, []) is rows
