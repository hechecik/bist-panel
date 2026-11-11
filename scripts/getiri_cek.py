#!/usr/bin/env python3
"""
Sabit getiri verisi — TR devlet tahvili + Eurobond.
Kaynak: borsapy (doviz.com/tahvil + Ziraat Yatırım eurobond).
Çıktı: data/getiri.json
Deterministik; yorum üretmez, sadece kaynaktan gelen sayıyı yazar.
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIKTI = os.path.join(KOK, "data", "getiri.json")


def tr_now():
    return datetime.now(timezone.utc) + timedelta(hours=3)


def tahvil_al_alternatif():
    """borsapy dışı yedek kaynak: doviz.com/tahvil sayfası doğrudan parse.

    borsapy `bp.bonds()` "Bond table not found on page" verdiğinde devreye girer
    (kanıt: 11.11.2026). Tablo satırları: "Türkiye 2 Yıllık Tahvil Faizi" | 39,440 | %0,18
    Yalnızca Türkiye satırları alınır. Bulunamazsa boş liste döner — uydurma değer yok.
    """
    import httpx
    from bs4 import BeautifulSoup

    url = "https://www.doviz.com/tahvil"
    r = httpx.get(url, timeout=20, follow_redirects=True,
                  headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    if r.status_code != 200:
        raise RuntimeError("HTTP %s" % r.status_code)
    soup = BeautifulSoup(r.text, "html.parser")
    rows = []
    for tr in soup.select("tr"):
        hucreler = [c.get_text(" ", strip=True) for c in tr.select("td")]
        if len(hucreler) < 2:
            continue
        ad = hucreler[0]
        if not ad.startswith("Türkiye") or "Tahvil Faizi" not in ad:
            continue
        vade = None
        for yil in ("2", "5", "10"):
            if ("%s Yıllık" % yil) in ad:
                vade = yil + "Y"
                break
        if not vade:
            continue

        def _sayi(t):
            t = t.replace("%", "").replace(".", "").replace(",", ".").strip()
            try:
                return float(t)
            except ValueError:
                return None

        getiri = _sayi(hucreler[1])
        degisim_yuzde = _sayi(hucreler[2]) if len(hucreler) > 2 else None
        if getiri is None or not (1.0 < getiri < 100.0):
            continue
        if any(x["vade"] == vade for x in rows):
            continue
        rows.append({"vade": vade, "ad": ad, "getiri": round(getiri, 2),
                     "degisim": None,
                     "degisim_yuzde": round(degisim_yuzde, 2) if degisim_yuzde is not None else None,
                     "kaynak": "doviz.com/tahvil"})
    rows.sort(key=lambda x: ["2Y", "5Y", "10Y"].index(x["vade"]) if x["vade"] in ["2Y", "5Y", "10Y"] else 9)
    return rows


def tahvil_al():
    """TR devlet tahvili 2Y/5Y/10Y — doviz.com (borsapy, yedek: doğrudan parse)."""
    import borsapy as bp
    try:
        df = bp.bonds()
    except Exception as e:
        # borsapy tabloyu bulamıyorsa alternatif kaynağa düş
        alt = tahvil_al_alternatif()
        if alt:
            return alt
        raise RuntimeError("borsapy: %s; alternatif kaynak: veri yok" % str(e)[:80])
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "vade": str(r["maturity"]),
            "ad": str(r["name"]),
            "getiri": round(float(r["yield"]), 2),
            "degisim": round(float(r["change"]), 3),
            "degisim_yuzde": round(float(r["change_pct"]), 2),
        })
    rows.sort(key=lambda x: ["2Y", "5Y", "10Y"].index(x["vade"]) if x["vade"] in ["2Y", "5Y", "10Y"] else 9)
    return rows


def eurobond_al():
    """TR Eurobond (USD/EUR) — Ziraat Bank kotasyonu. Vadeye göre sıralı.

    Alan adları Ziraat başlıklarıyla birebir eşleşir:
      Alış  = bankanın sizden alışı  (siz satarken geçerli fiyat/oran)
      Satış = bankanın size satışı   (siz alırken geçerli fiyat/oran)
    borsapy bid_* -> Ziraat Alış, borsapy ask_* -> Ziraat Satış.
    """
    import borsapy as bp
    df = bp.eurobonds()

    def n(x):
        try:
            v = float(x)
            return round(v, 2) if v == v else None  # NaN kontrolü
        except Exception:
            return None

    rows = []
    for _, r in df.iterrows():
        try:
            mat = r["maturity"]
            vade = mat.strftime("%d.%m.%Y") if hasattr(mat, "strftime") else str(mat)
            rows.append({
                "isin": str(r["isin"]),
                "vade": vade,
                "kalan_gun": int(r["days_to_maturity"]),
                "para": str(r.get("currency", "USD")),
                "alis_fiyat": n(r["bid_price"]),
                "alis_oran": n(r["bid_yield"]),
                "satis_fiyat": n(r["ask_price"]),
                "satis_oran": n(r["ask_yield"]),
            })
        except Exception:
            continue
    rows.sort(key=lambda x: x["kalan_gun"])
    return rows


def main():
    out = {
        "uretildi": tr_now().replace(tzinfo=None).isoformat(timespec="seconds"),
        "kaynak": "borsapy · doviz.com/tahvil + Ziraat Yatırım eurobond",
        "tahvil": [],
        "eurobond": [],
        "risk_free": None,
        "hatalar": [],
    }

    try:
        out["tahvil"] = tahvil_al()
    except Exception as e:
        out["hatalar"].append("tahvil: " + str(e)[:160])

    # Tahvil boşsa sessizce gizleme — sebebi yaz
    if not out["tahvil"]:
        detay = [h for h in out["hatalar"] if h.startswith("tahvil:")]
        out["tahvil_durum"] = ("kaynak boş — " + (detay[0][8:] if detay else "bilinmeyen hata; "
                               "borsapy doviz.com tablosunu bulamadı, alternatif kaynak da veri vermedi"))
    else:
        kaynaklar = {x.get("kaynak", "borsapy") for x in out["tahvil"]}
        out["tahvil_durum"] = "ok — " + ", ".join(sorted(kaynaklar))

    try:
        import borsapy as bp
        rf = bp.risk_free_rate()
        if rf is not None:
            out["risk_free"] = round(float(rf) * 100, 2)
    except Exception:
        pass

    try:
        out["eurobond"] = eurobond_al()
    except Exception as e:
        out["hatalar"].append("eurobond: " + str(e)[:160])

    # Özet: en düşük/en yüksek satış oranı + vade uçları
    eb = out["eurobond"]
    if eb:
        gecerli = [x for x in eb if x.get("satis_oran") is not None]
        if gecerli:
            en_dusuk = min(gecerli, key=lambda x: x["satis_oran"])
            en_yuksek = max(gecerli, key=lambda x: x["satis_oran"])
            out["eurobond_ozet"] = {
                "adet": len(eb),
                "para": sorted({x["para"] for x in eb}),
                "ilk_vade": gecerli[0]["vade"],
                "son_vade": gecerli[-1]["vade"],
                "min_satis_oran": en_dusuk["satis_oran"],
                "min_satis_vade": en_dusuk["vade"],
                "max_satis_oran": en_yuksek["satis_oran"],
                "max_satis_vade": en_yuksek["vade"],
            }

    os.makedirs(os.path.dirname(CIKTI), exist_ok=True)
    if not out["tahvil"] and not out["eurobond"]:
        # Hiç veri yoksa mevcut dosyayı ezme, hata ile çık (CI alarmı)
        print("HATA: ne tahvil ne eurobond verisi alınamadı -> " + "; ".join(out["hatalar"]))
        sys.exit(1)
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("getiri.json yazıldı | tahvil: %d | eurobond: %d | risk_free: %s"
          % (len(out["tahvil"]), len(out["eurobond"]), out["risk_free"]))
    if out["hatalar"]:
        print("uyarı: " + "; ".join(out["hatalar"]))


if __name__ == "__main__":
    main()
