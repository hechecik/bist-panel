"""G11 — Altın Senaryo Motoru v2 saf fonksiyon testleri (ağa çıkmaz)."""
import datetime as dt

import pytest

from scripts.altin_cek import (
    DONEM_BAR, ESIK_BRENT_5G_PCT, ESIK_BRENT_PCT, ESIK_DOT_BP, ESIK_DXY_PCT, ESIK_GRAM_SAPMA_PCT,
    ESIK_REEL_FAIZ_BP, HIZALAMA_TOLERANS_GUN, KARNE_MAKS, KUR_UYARI_KAT, ayrisim_uyarisi, bant,
    donem_degisimleri, gram_ayrisim, gram_gercek_kontrol, gram_serisi, karne_blogu, karne_ekle,
    karne_isabet, karne_zamani_mi, kur_trend, kur_tutarlilik_uyarisi, makro_skor, senaryolar,
    seri_degisim, tarihe_gore_deger, teknik_skor, tr_saat,
)


# ── teknik skor ──────────────────────────────────────────────
def test_teknik_skor_trend_artirsi_ve_rsi():
    # trend +2, RSI 60 → +1, 1a +5 → +1  ⇒ +4 (52h konum artık sayılmıyor)
    v = {'trend_skor': 2, 'rsi': 60, 'konum_52h': 95}
    assert teknik_skor(v, {'1a': 5.0}) == 4


def test_teknik_skor_ayi_tarafi():
    v = {'trend_skor': -2, 'rsi': 30, 'konum_52h': 5}
    assert teknik_skor(v, {'1a': -5.0}) == -4


def test_teknik_skor_bos_vitrinde_none():
    assert teknik_skor(None, {'1a': 5}) is None
    assert teknik_skor({}, {'1a': 5}) is None   # trend_skor yok = skor üretilemez


def test_teknik_skor_52h_konum_sayilmiyor():
    """Regresyon: momentum tekrarı kaldırıldı — konum değişince skor değişmemeli."""
    a = {'trend_skor': 1, 'rsi': 50, 'konum_52h': 99}
    b = {'trend_skor': 1, 'rsi': 50, 'konum_52h': 1}
    assert teknik_skor(a, {}) == teknik_skor(b, {})


def test_teknik_skor_performans_eksikse_atlanir():
    v = {'trend_skor': 2, 'rsi': 60}
    assert teknik_skor(v, {}) == 3
    assert teknik_skor(v, {'1a': None}) == 3


# ── makro skor ──────────────────────────────────────────────
def _makro(reel_bp=None, dxy=None, makas=None, brent=None):
    m = {'durum': 'ok', 'seriler': {}, 'piyasa': {}, 'dot_plot': {}}
    if reel_bp is not None:
        m['seriler']['DFII10'] = {'degisim_20g': reel_bp / 100}
    if dxy is not None:
        m['piyasa']['dxy'] = {'degisim_20g_pct': dxy}
    if makas is not None:
        m['dot_plot']['makas_bp'] = makas
    if brent is not None:
        m['piyasa']['brent'] = {'degisim_20g_pct': brent}
    return m


def test_makro_skor_boga_bilesenleri():
    m = _makro(reel_bp=-20, dxy=-1.5, makas=40, brent=12)
    r = makro_skor(m)
    assert r['skor'] == 4 and r['maks'] == 4 and r['durum'] == 'ok'
    assert set(r['bilesenler']) == {'reel_faiz', 'dxy', 'dot_makas', 'brent'}


def test_makro_skor_ayi_bilesenleri():
    r = makro_skor(_makro(reel_bp=25, dxy=2.0, makas=-30, brent=-15))
    assert r['skor'] == -4


def test_makro_skor_esik_alti_notr():
    r = makro_skor(_makro(reel_bp=5, dxy=0.5, makas=0, brent=3))
    assert r['skor'] == 0 and r['maks'] == 4


def test_makro_skor_esik_siniri_dahil():
    r = makro_skor(_makro(reel_bp=-ESIK_REEL_FAIZ_BP, dxy=-ESIK_DXY_PCT,
                          makas=ESIK_DOT_BP, brent=ESIK_BRENT_PCT))
    assert r['skor'] == 4


def test_makro_skor_eksik_bilesen_maks_dusurur():
    r = makro_skor(_makro(dxy=-2.0))
    assert r['skor'] == 1 and r['maks'] == 1


def test_makro_skor_veri_yok():
    for m in (None, {}, {'durum': 'veri yok'}, _makro()):
        r = makro_skor(m)
        assert r['skor'] is None and r['maks'] == 0


def test_makro_skor_agir_cikmaz():
    """Saf fonksiyon: ağ erişimi olmadan anında dönmeli (veri hazır verilir)."""
    r = makro_skor(_makro(reel_bp=15, dxy=1.2, makas=-25, brent=-11))
    assert r['skor'] == -4   # reel -1, DXY -1, dot makası -1, Brent -1
    assert r['maks'] == 4


# ── ayrışma uyarısı ─────────────────────────────────────────
def test_ayrisim_zit_isaret():
    var, metin = ayrisim_uyarisi(3, -2)
    assert var is True and '⚠️' in metin and 'ayrış' in metin


def test_ayrisim_ayni_yon():
    assert ayrisim_uyarisi(3, 2)[0] is False
    assert ayrisim_uyarisi(-3, -2)[0] is False


def test_ayrisim_zayif_makro_ayrisim_sayilmaz():
    """Regresyon: makro ±1 iken 'makro BOĞA' iddiası üretilmemeli (canlı veride görüldü)."""
    var, metin = ayrisim_uyarisi(-4, 1)
    assert var is False and 'BOĞA' not in metin


def test_ayrisim_notr_veya_eksik():
    assert ayrisim_uyarisi(0, -2)[0] is False
    assert ayrisim_uyarisi(None, -2)[0] is False
    assert ayrisim_uyarisi(1, None)[0] is False


# ── bant / ATR ──────────────────────────────────────────────
def test_bant_atr_karekok5():
    alt, ust = bant(2000.0, 10.0, 1.0)
    d = 10.0 * (5 ** 0.5)
    assert alt == pytest.approx(2000 - d, abs=0.05)
    assert ust == pytest.approx(2000 + d, abs=0.05)
    assert alt < 2000 < ust


def test_bant_katsayi_buyudukce_genisler():
    a1, u1 = bant(2000.0, 10.0, 1.0)
    a2, u2 = bant(2000.0, 10.0, 2.0)
    assert (u2 - a2) == pytest.approx(2 * (u1 - a1), abs=0.5)   # 0,1$ yuvarlama payı


def test_bant_negatif_k_normalize_edilir():
    """k işareti yönü taşır; bant daima alt < son < ust döner."""
    assert bant(2000.0, 10.0, -1.0) == bant(2000.0, 10.0, 1.0)


def test_bant_veri_yok():
    assert bant(None, 10.0, 1.0) == (None, None)
    assert bant(2000.0, 0, 1.0) == (None, None)


# ── senaryolar ──────────────────────────────────────────────
def test_senaryo_dort_artı_cakisma():
    m = _makro(reel_bp=-15, dxy=-2.0, makas=10, brent=5)
    m['piyasa']['brent']['degisim_5g'] = 1.0
    m['piyasa']['brent']['son'] = 80.0
    r = senaryolar(m, 2000.0, 10.0)
    adlar = [s['ad'] for s in r['liste']]
    assert adlar[:4] == ['Fiyatlanmış', 'Şahin sürpriz', 'Güvercin sürpriz', 'Jeopolitik şok']
    assert r['liste'][-1]['ad'].startswith('Çakışma')
    assert r['liste'][-1].get('cakisma') is True


def test_senaryo_yon_ve_vurgu_ayrisir():
    """Regresyon: canlı çıktıda 4 senaryo aynı bandı gösteriyordu — yön alanı ayrışmalı."""
    r = senaryolar(_makro(makas=10, brent=0), 2000.0, 10.0)
    d = {s['ad']: s for s in r['liste'] if not s.get('cakisma')}
    assert d['Şahin sürpriz']['vurgu'] == 'alt' and d['Şahin sürpriz']['yon'] == 'aşağı'
    assert d['Güvercin sürpriz']['vurgu'] == 'üst' and d['Güvercin sürpriz']['yon'] == 'yukarı'
    assert d['Jeopolitik şok']['k'] == 2.0 and d['Fiyatlanmış']['vurgu'] is None


def test_senaryo_bantlar_atr_ile_tutarli():
    m = _makro(makas=0, brent=0)
    r = senaryolar(m, 2000.0, 10.0)
    for s in r['liste']:
        alt, ust = s['bant']
        assert alt < 2000 < ust          # bant daima normalize
        assert ust - alt == pytest.approx(2 * abs(s['k']) * 10.0 * (5 ** 0.5), abs=0.2)


def test_senaryo_olasilik_yoksa_gizlenir():
    """ZQ'den türetilemiyorsa olasilik None + sütun gizli — elle yüzde yok."""
    r = senaryolar(_makro(makas=50), 2000.0, 10.0)
    assert r['olasilik_goster'] is False
    for s in r['liste']:
        assert s['olasilik'] is None
    assert 'ZQ' in r['not'] or 'vadeli' in r['not']


def test_senaryo_gerceklesti_bayraklari():
    m = _makro(makas=5, brent=20)
    m['dot_plot']['revizyon'] = {'degisim_bp': 30}
    m['piyasa']['brent']['degisim_5g'] = 15.0
    m['piyasa']['brent']['son'] = 100.0
    r = senaryolar(m, 2000.0, 10.0)
    d = {s['ad']: s['gerceklesti'] for s in r['liste']}
    assert d['Şahin sürpriz'] is True
    assert d['Güvercin sürpriz'] is False
    assert r['liste'][-1]['gerceklesti'] is True  # çakışma


def test_senaryo_makro_yok_cokme():
    r = senaryolar(None, 2000.0, 10.0)
    assert len(r['liste']) == 5
    assert all(s['olasilik'] is None for s in r['liste'])


# ── kur trendi ──────────────────────────────────────────────
def _seri(degerler, bas=dt.date(2025, 1, 1)):
    return [(bas + dt.timedelta(days=i), float(x)) for i, x in enumerate(degerler)]


def test_kur_trend_aylik_kayip():
    s = _seri([10.0 * (1.001 ** i) for i in range(70)])   # günlük %0,1 → aylık ≈ %2,1
    r = kur_trend(s)
    assert r['gun'] == 63
    assert 1.5 < r['aylik_kayip_pct'] < 2.6


def test_kur_trend_yetersiz_veri():
    assert kur_trend([]) == {'durum': 'veri yok'}
    assert kur_trend(_seri([10, 11]))['durum'] == 'veri yok'
    assert kur_trend(None)['durum'] == 'veri yok'


def test_kur_trend_sifir_baz():
    assert kur_trend(_seri([0.0] * 30))['durum'] == 'veri yok'


# ── gram ayrışımı ───────────────────────────────────────────
def test_gram_ayrisim_toplam_ve_pay():
    r = gram_ayrisim({'1a': 4.0}, {'1a': 2.0})
    assert r['1a']['gram_pct'] == pytest.approx(6.0)
    assert r['1a']['ons_pay'] == pytest.approx(66.7, abs=0.1)
    assert r['1a']['kur_pay'] == pytest.approx(33.3, abs=0.1)


def test_gram_ayrisim_bilesen_eksik():
    r = gram_ayrisim({'1a': {'pct': 3.0}}, {})
    assert r['1a']['gram_pct'] == pytest.approx(3.0)
    assert r['1a']['kur_pct'] == 0.0
    assert r['1a']['not']


def test_gram_ayrisim_veri_yok():
    r = gram_ayrisim({}, {})
    for k in ('1g', '1h', '1a'):
        assert r[k] == {'durum': 'veri yok'}


def test_gram_ayrisim_sifir_toplamda_pay_none():
    r = gram_ayrisim({'1g': 1.0}, {'1g': -1.0})
    assert r['1g']['gram_pct'] == pytest.approx(0.0)
    assert r['1g']['ons_pay'] is None and r['1g']['kur_pay'] is None


def test_gram_gercek_kontrol_kabul():
    ons = _seri([2000 + i for i in range(30)])
    kur = _seri([40 + 0.2 * i for i in range(30)])
    r = gram_gercek_kontrol(ons, kur, bar=21)
    assert r['kabul'] is True
    # tolerans çapraz terime göre genişler, sabit eşik değil
    assert r['sapma_pct'] <= r['tolerans_pct']
    assert r['tolerans_pct'] >= ESIK_GRAM_SAPMA_PCT


def test_gram_gercek_kontrol_veri_yok():
    assert gram_gercek_kontrol([], [])['durum'] == 'veri yok'
    assert gram_gercek_kontrol(_seri([1] * 5), _seri([1] * 5), bar=21)['durum'] == 'veri yok'


# ── karne ───────────────────────────────────────────────────
def test_karne_ekle_ayni_tarih_tek_kayit():
    k = [{'tarih': '2026-01-01', 'ons': 2000}]
    k = karne_ekle(k, {'tarih': '2026-01-01', 'ons': 2100})
    assert len(k) == 1 and k[0]['ons'] == 2100


def test_karne_ekle_siralar_ve_sinirlar():
    k = []
    for i in range(1, 8):
        k = karne_ekle(k, {'tarih': f'2026-01-0{i}', 'ons': i}, maks=5)
    assert len(k) == 5
    assert k[-1]['tarih'] == '2026-01-07'
    assert [x['tarih'] for x in k] == sorted(x['tarih'] for x in k)


def test_karne_maks_sabiti_400():
    assert KARNE_MAKS == 400


def test_karne_isabet_boga_dogru():
    gunler = _seri(list(range(100, 130)))   # her gün +1
    kayit = [{'tarih': gunler[0][0].isoformat(), 'ons': 100.0, 'bias': 'BOĞA'}]
    r = karne_isabet(kayit, gunler, ufuklar=(5, 20))
    assert r['5g']['isabet_pct'] == 100.0 and r['5g']['ornek'] == 1
    assert r['20g']['isabet_pct'] == 100.0


def test_karne_isabet_yanlis_yon():
    gunler = _seri(list(range(100, 130)))
    kayit = [{'tarih': gunler[0][0].isoformat(), 'ons': 100.0, 'bias': 'AYI'}]
    r = karne_isabet(kayit, gunler, ufuklar=(5,))
    assert r['5g']['isabet_pct'] == 0.0


def test_karne_isabet_notr_ve_eksik_ufuk_sayilmaz():
    gunler = _seri(list(range(100, 110)))
    kayit = [{'tarih': gunler[0][0].isoformat(), 'ons': 100.0, 'bias': 'NÖTR'},
             {'tarih': gunler[-1][0].isoformat(), 'ons': 109.0, 'bias': 'BOĞA'}]
    r = karne_isabet(kayit, gunler, ufuklar=(5, 20))
    assert r['5g']['ornek'] == 0 and r['5g']['isabet_pct'] is None
    assert r['20g']['ornek'] == 0


def test_karne_blogu_bos_uydurmaz():
    r = karne_blogu([], _seri([1] * 30))
    assert r['durum'] == 'veri yok'
    assert 'uydurulmaz' in r['not']


def test_karne_blogu_ozet():
    gunler = _seri(list(range(100, 130)))
    kayit = [{'tarih': gunler[0][0].isoformat(), 'ons': 100.0, 'bias': 'BOĞA'},
             {'tarih': gunler[10][0].isoformat(), 'ons': 110.0, 'bias': 'BOĞA'}]
    r = karne_blogu(kayit, gunler)
    assert r['durum'] == 'ok' and r['kayit_sayisi'] == 2
    assert r['son_tarih'] == gunler[10][0].isoformat()


# ── zaman dilimi ────────────────────────────────────────────
def test_tr_saat_utc_arti_3():
    u = dt.datetime(2026, 1, 15, 20, 0, tzinfo=dt.timezone.utc)
    t = tr_saat(u)
    assert t.hour == 23 and t.utcoffset() == dt.timedelta(hours=3)


def test_karne_zamani_23te_dogru():
    assert karne_zamani_mi(dt.datetime(2026, 1, 15, 20, 0, tzinfo=dt.timezone.utc)) is True
    assert karne_zamani_mi(dt.datetime(2026, 1, 15, 20, 40, tzinfo=dt.timezone.utc)) is True
    assert karne_zamani_mi(dt.datetime(2026, 1, 15, 18, 0, tzinfo=dt.timezone.utc)) is False
    assert karne_zamani_mi(dt.datetime(2026, 1, 15, 22, 0, tzinfo=dt.timezone.utc)) is False


# ── DÜZELTME: pencere (1g/1h/1a iş günü) + tarihe göre hizalama ──────────────
def _isg_seri(degerler, bas=dt.date(2026, 1, 5)):
    """İş günü (Pzt–Cum) serisi üret: [(date, float)] eskiden yeniye."""
    out, t, i = [], bas, 0
    while len(out) < len(degerler):
        if t.weekday() < 5:
            out.append((t, float(degerler[i])))
            i += 1
        t += dt.timedelta(days=1)
    return out


def test_pencereler_is_gunu_1g_1h_1a():
    # 1a = 21 iş günü (1 ay), 252 DEĞİL — pencere hatası regresyon testi
    assert DONEM_BAR == {'1g': 1, '1h': 5, '1a': 21}


def test_donem_degisimleri_is_gunu_bazli():
    # her iş günü +%1 → 1g %1, 1h ~%5, 1a ~%21 (yıllık %1000 DEĞİL)
    seri = _isg_seri([100 * (1.01 ** i) for i in range(60)])
    d = donem_degisimleri(seri)
    assert d['1g']['pct'] == pytest.approx(1.0, abs=0.05)
    assert d['1h']['pct'] == pytest.approx(5.1, abs=0.4)
    assert d['1a']['pct'] == pytest.approx(23.2, abs=1.5)
    assert d['1a']['bar'] == 21


def test_seri_degisim_aylik_pencerede_baslangic_tarihi():
    seri = _isg_seri([100 + i for i in range(40)])
    r = seri_degisim(seri, DONEM_BAR['1a'])
    assert r['bas_tarih'] and r['son_tarih']
    fark = (dt.date.fromisoformat(r['son_tarih']) - dt.date.fromisoformat(r['bas_tarih'])).days
    # 21 iş günü ≈ 29 takvim günü — YIL değil
    assert 27 <= fark <= 33, f'1a penceresi ~1 ay olmalı, {fark} gün çıktı'


def test_tarihe_gore_deger_eksik_gun_oncekini_kullanir():
    seri = [(dt.date(2026, 1, 5), 10.0), (dt.date(2026, 1, 9), 20.0)]
    # 2026-01-07 seride yok → en yakın ÖNCEKİ (01-05)
    assert tarihe_gore_deger(seri, dt.date(2026, 1, 7)) == (dt.date(2026, 1, 5), 10.0)
    # hafta sonu → cuma
    assert tarihe_gore_deger(seri, dt.date(2026, 1, 10)) == (dt.date(2026, 1, 9), 20.0)


def test_tarihe_gore_deger_tolerans_asilirsa_none():
    seri = [(dt.date(2026, 1, 5), 10.0)]
    assert tarihe_gore_deger(seri, dt.date(2026, 1, 5 + HIZALAMA_TOLERANS_GUN + 1)) is None
    assert tarihe_gore_deger(seri, dt.date(2026, 1, 4)) is None   # hedef öncesi veri yok


def test_seri_degisim_index_kaymasi_yapmaz():
    # ons her iş günü var; kurda 10 günlük BOŞLUK var. Index ile hizalama yanlış tarihe bakardı.
    ons = _isg_seri([2000.0] * 40)                 # sabit ons → ons değişimi %0
    kur = _isg_seri([40.0 + 0.1 * i for i in range(40)])
    kur_kopuk = [x for i, x in enumerate(kur) if not (18 <= i <= 27)]
    d_ons = donem_degisimleri(ons)['1a']
    d_kur = donem_degisimleri(kur_kopuk)['1a']
    assert d_ons['pct'] == pytest.approx(0.0, abs=1e-9)
    # kopuk seride de baz, hedef tarihe en yakın önceki gün → kur artışı makul, uçuk değil
    assert d_kur['pct'] is None or 0 < d_kur['pct'] < 12


def test_seri_degisim_veri_yok_kisa_seri():
    assert seri_degisim([], 21)['durum'] == 'veri yok'
    assert seri_degisim(_isg_seri([1.0] * 10), 21)['durum'] == 'veri yok'


def test_seri_degisim_sifir_baz_pct_yok():
    # baz (1 gün önce) 0 → yüzde ÜRETİLMEZ (sıfıra bölme/uydurma yok)
    seri = _isg_seri([5.0] * 30 + [0.0])
    r = seri_degisim(seri, 1)
    assert r['durum'] == 'veri yok' and 'pct' not in r
    # baz 0 ama SON değer var: 2 gün önce 0 → hedef 0 → veri yok
    seri2 = _isg_seri([5.0] * 29 + [0.0, 7.0])
    r2 = seri_degisim(seri2, 1)
    assert r2['durum'] == 'veri yok' and 'pct' not in r2


def test_gram_serisi_bagimsiz_ve_hizali():
    ons = _isg_seri([2000.0 + i for i in range(30)])
    kur = _isg_seri([40.0 + 0.1 * i for i in range(30)])
    gs = gram_serisi(ons, kur)
    assert len(gs) == 30
    assert gs[0][1] == pytest.approx(2000.0 / 31.1034768 * 40.0, rel=1e-9)


def test_gram_gercek_kontrol_pencere_hatasini_tekrarlamaz():
    # 1a kontrolü ~1 ay olmalı: gram serisi 1 yıllık değişimi göstermemeli
    ons = _isg_seri([2000.0] * 300)
    kur = _isg_seri([40.0 * (1.0065 ** i) for i in range(300)])
    r = gram_gercek_kontrol(ons, kur, bar=21)
    assert r['kabul'] is True
    assert r['yaklasik_pct'] < 20, f'1a ~1 ay olmalı, %{r["yaklasik_pct"]} çıktı'
    fark = (dt.date.fromisoformat(r['son_tarih']) - dt.date.fromisoformat(r['bas_tarih'])).days
    assert 28 <= fark <= 35


def test_kur_tutarlilik_uyarisi_esik_asilinca_uyarir():
    # aylık varsayım %1,65 → eşik %4,95; 1a %18,62 pencere hatası UYARI vermeli
    donem = {'1g': {'pct': 0.1}, '1h': {'pct': 0.4}, '1a': {'pct': 18.62}}
    r = kur_tutarlilik_uyarisi(donem, {'aylik_kayip_pct': 1.65})
    assert r['var'] is True
    assert r['esik_pct'] == pytest.approx(4.95, abs=0.01)
    assert any(u['donem'] == '1a' for u in r['uyarilar'])


def test_kur_tutarlilik_uyarisi_makul_degisimde_susar():
    donem = {'1g': {'pct': 0.1}, '1h': {'pct': 0.4}, '1a': {'pct': 1.2}}
    assert kur_tutarlilik_uyarisi(donem, {'aylik_kayip_pct': 1.65})['var'] is False


def test_kur_tutarlilik_uyarisi_aylik_yoksa_denetlemez():
    r = kur_tutarlilik_uyarisi({'1a': {'pct': 50.0}}, {'durum': 'veri yok'})
    assert r['var'] is False and r['aylik_pct'] is None


def test_kur_uyari_kat_sabiti():
    assert KUR_UYARI_KAT == 3.0


# ── jeopolitik şok tek yön gösterimi ────────────────────────
def test_jeopolitik_sok_tek_yon_ust_bant():
    makro = {'dot_plot': {'makas_bp': None, 'piyasa_ima': {}},
             'seriler': {'reel_faiz_20g_bp': -20.0, 'brent_5g_pct': 20.0},
             'piyasa': {}}
    s = senaryolar(makro, son=4000.0, atr=90.0)
    j = [x for x in s['liste'] if x['ad'] == 'Jeopolitik şok'][0]
    assert j['yon'] == 'yukarı'
    # yön yukarı → gösterim yalnız üst bant (iki yönlü aralık DEĞİL)
    assert j['bant_gosterim'] == [j['bant'][1], j['bant'][1]]
    assert j['bant_gosterim'][0] != j['bant'][0]
