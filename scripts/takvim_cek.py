#!/usr/bin/env python3
"""
Takvim verisi — Halka Arz (IPO) + Temettü.
Kaynak: halkarz.com (HTML liste sayfaları + temettu.php JSON API).
Çıktı: data/takvim.json
Deterministik; yorum üretmez.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CIKTI = os.path.join(KOK, "data", "takvim.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"

AYLAR = {
    "ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "mayis": 5,
    "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9,
    "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12,
}


def tr_now():
    return datetime.now(timezone.utc) + timedelta(hours=3)


def cek(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def _cls(blok, cls):
    m = re.search(re.escape(cls) + r'"[^>]*>\s*(.*?)\s*</', blok, re.S)
    if not m:
        return ""
    return re.sub(r"<[^>]+>", " ", m.group(1)).strip()


def parse_arz_listesi(html):
    """main + arşiv sayfalarındaki <article class="index-list"> bloklarını ayrıştır."""
    out = []
    for a in re.findall(r'<article class="index-list">(.*?)</article>', html, re.S):
        kod = _cls(a, "il-bist-kod")
        m = re.search(r'il-halka-arz-sirket"><a[^>]*>(.*?)</a>', a, re.S)
        sirket = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
        mt = re.search(r"<time[^>]*>(.*?)</time>", a, re.S)
        tarih = re.sub(r"\s+", " ", mt.group(1)).strip() if mt else ""
        if sirket:
            out.append({"kod": kod, "sirket": sirket, "tarih": tarih})
    return out


def tarih_sirala_anahtari(tarih_str):
    """'9-10-11 Eylül 2026' -> (yil, ay, gun). Bilinmeyen -> çok geri."""
    if not tarih_str:
        return (0, 0, 0)
    yil_m = re.search(r"(20\d{2})", tarih_str)
    yil = int(yil_m.group(1)) if yil_m else 0
    ay = 0
    low = tarih_str.lower()
    for ad, no in AYLAR.items():
        if ad in low:
            ay = no
            break
    gun_m = re.findall(r"\b(\d{1,2})\b", tarih_str.split(" ", 1)[0])
    gun = int(gun_m[-1]) if gun_m else 0
    return (yil, ay, gun)


def durum_bul(tarih_str):
    low = (tarih_str or "").lower()
    if "ertel" in low:
        return "ertelendi"
    if "iptal" in low:
        return "iptal"
    if not tarih_str:
        return "basvuru"
    try:
        y, m, d = tarih_sirala_anahtari(tarih_str)
        if y and m and d:
            dt = datetime(y, m, d)
            bugun = tr_now().replace(tzinfo=None)
            if dt < bugun - timedelta(days=1):
                return "tamamlandi"
            return "yaklasan"
    except Exception:
        pass
    return "bilinmiyor"


def temettu_al():
    url = "https://halkarz.com/wp-content/themes/halkarz/api/temettu.php?v=%d" % int(tr_now().timestamp())
    raw = cek(url, timeout=30)
    data = json.loads(raw)

    def sayi(x):
        try:
            return float(str(x).replace(".", "").replace(",", ".")) if "," in str(x) else float(str(x))
        except Exception:
            return None

    rows = []
    bugun = tr_now().replace(tzinfo=None)
    for x in data:
        t = (x.get("t_tarih") or "").strip()
        try:
            dt = datetime.strptime(t, "%d.%m.%Y")
        except Exception:
            dt = None
        rows.append({
            "kod": (x.get("t_bistkod") or "").strip(),
            "sirket": re.sub(r"\s+", " ", (x.get("t_sirket") or "")).strip(),
            "net": sayi(x.get("t_temt_net")),
            "yuzde": sayi(x.get("t_yuzde")),
            "tarih": t,
            "gecmis": bool(dt and dt < bugun),
            "gun_fark": (dt - bugun).days if dt else None,
        })
    # Yaklaşanlar önce, sonra geçmiş (en yeni geçmiş)
    rows.sort(key=lambda r: (1 if r["gecmis"] else 0, abs(r["gun_fark"]) if r["gun_fark"] is not None else 10**6))
    return rows


def main():
    out = {
        "uretildi": tr_now().replace(tzinfo=None).isoformat(timespec="seconds"),
        "kaynak": "halkarz.com",
        "halka_arz": [],
        "basvuru": [],
        "ertelenen": [],
        "temettu": [],
        "hatalar": [],
    }

    # 1) Yakın zamanda gerçekleşen/planlı halka arzlar (ana sayfa)
    try:
        ana = cek("https://halkarz.com/")
        arz = parse_arz_listesi(ana)
        seen = set()
        clean = []
        for x in arz:
            key = (x["kod"], x["sirket"])
            if key in seen:
                continue
            seen.add(key)
            x["durum"] = durum_bul(x["tarih"])
            clean.append(x)
        # Ertelenen/iptal ayrı; kalan tarihli liste
        out["halka_arz"] = [x for x in clean if x["durum"] != "ertelendi"][:40]
        out["ertelenen"] = [x for x in clean if x["durum"] == "ertelendi"][:20]
    except Exception as e:
        out["hatalar"].append("halka_arz: " + str(e)[:160])

    # 2) Başvuru sürecindekiler (henüz kod/tarih yok — pipeline)
    try:
        bs = cek("https://halkarz.com/k/halka-arz/basvuru-surecinde/")
        g = []
        for m in re.finditer(r'il-halka-arz-sirket">\s*<a[^>]*>(.*?)</a>', bs, re.S):
            ad = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
            if ad and ad not in g:
                g.append(ad)
        out["basvuru"] = g[:60]
    except Exception as e:
        out["hatalar"].append("basvuru: " + str(e)[:160])

    # 3) Temettü takvimi (JSON API)
    try:
        out["temettu"] = temettu_al()
    except Exception as e:
        out["hatalar"].append("temettu: " + str(e)[:160])

    os.makedirs(os.path.dirname(CIKTI), exist_ok=True)
    if not out["halka_arz"] and not out["temettu"] and not out["basvuru"]:
        print("HATA: takvim verisi alınamadı -> " + "; ".join(out["hatalar"]))
        sys.exit(1)
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("takvim.json | halka_arz: %d | başvuru: %d | ertelenen: %d | temettü: %d"
          % (len(out["halka_arz"]), len(out["basvuru"]), len(out["ertelenen"]), len(out["temettu"])))
    if out["hatalar"]:
        print("uyarı: " + "; ".join(out["hatalar"]))


if __name__ == "__main__":
    main()
