#!/usr/bin/env python3
"""bist-panel harici tetikleyici — Hermes cron ile calisir (no_agent, LLM'siz).

Token koda YAZILMAZ; ortam degiskeninden okunur (GITHUB_TOKEN / GH_TOKEN).
Yoksa yerel makinede ~/.git-credentials dosyasina duser (repoda boyle bir dosya yok).

Neden: GitHub'in kendi `schedule` mekanizmasi bu repoda fiilen tetiklenmiyor.
cron-job.org hesabi/kimligi yok; fine-grained PAT de paneldan elle uretilmeli.
Elimizdeki token `workflow` scope'lu ve workflow_dispatch cagirabiliyor (204).

Bu script: zamanlanmis is akislarindan gecikmis olani workflow_dispatch ile tetikler.
Zaman pencereleri Europe/Istanbul (UTC+3) ile hesaplanir.

Cikti sozlesmesi (sessiz mod):
  - Tetikleme/gecikme satirlari stdout'a DEGIL, ~/.hermes/logs/harici_tetik.log dosyasina yazilir.
  - stdout'a SADECE hata yazilir (FAIL, HTTP hatasi, token yok, tetik basarisiz).
    Boylece Telegram'a yalnizca bir sey bozuldugunda mesaj gider.
  - Log dosyasi 1 MB'i gecerse eski yarisi kirpilir.
"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

REPO = "hechecik/bist-panel"
API = "https://api.github.com"
CRED = os.path.expanduser("~/.git-credentials")
TR = dt.timezone(dt.timedelta(hours=3))  # Europe/Istanbul, kalici UTC+3 (DST yok)

LOG_DOSYA = os.path.expanduser("~/.hermes/logs/harici_tetik.log")
LOG_MAKS_BAYT = 1024 * 1024  # 1 MB


def token() -> str:
    for ad in ("GITHUB_TOKEN", "GH_TOKEN"):
        deger = os.environ.get(ad, "").strip()
        if deger:
            return deger
    with open(CRED, encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if "github.com" in satir and "://" in satir:
                # https://user:TOKEN@github.com
                kimlik = satir.split("://", 1)[1].split("@", 1)[0]
                if ":" in kimlik:
                    return kimlik.split(":", 1)[1]
    raise SystemExit("FAIL token bulunamadi: GITHUB_TOKEN/GH_TOKEN veya ~/.git-credentials")


def log_yaz(satirlar) -> None:
    """Satirlari log dosyasina ekler; dosya 1 MB'i gecerse eski yarisini kirpar."""
    if not satirlar:
        return
    try:
        os.makedirs(os.path.dirname(LOG_DOSYA), exist_ok=True)
        with open(LOG_DOSYA, "a", encoding="utf-8") as f:
            for s in satirlar:
                f.write(s + "\n")
        if os.path.getsize(LOG_DOSYA) > LOG_MAKS_BAYT:
            with open(LOG_DOSYA, "rb") as f:
                f.seek(LOG_MAKS_BAYT // 2)
                kuyruk = f.read()
            # ilk yarim satiri at (bozuk satir basi olmasin)
            if b"\n" in kuyruk:
                kuyruk = kuyruk.split(b"\n", 1)[1]
            with open(LOG_DOSYA, "wb") as f:
                f.write(kuyruk)
    except OSError as e:
        # Log yazilamazsa bu bir hatadir -> stdout (Telegram'a gider)
        print(f"FAIL log yazilamadi: {LOG_DOSYA}: {e}")


def api(tok, yol, method="GET", govde=None):
    veri = json.dumps(govde).encode() if govde is not None else None
    req = urllib.request.Request(API + yol, data=veri, method=method)
    req.add_header("Authorization", "token " + tok)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "bist-panel-harici-tetik")
    if veri:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        ham = r.read().decode()
        return r.status, (json.loads(ham) if ham.strip() else None)


def son_calisma(tok, akis):
    """(gecikme_dk, son_metin) — hic calisma yoksa gecikme 10**6."""
    _, d = api(tok, f"/repos/{REPO}/actions/workflows/{akis}.yml/runs?per_page=1&branch=main")
    kosular = d.get("workflow_runs") or []
    if not kosular:
        return 10**6, "hic calisma yok", None
    son = kosular[0]
    ts = dt.datetime.fromisoformat(son["created_at"].replace("Z", "+00:00"))
    gecen = (dt.datetime.now(dt.timezone.utc) - ts).total_seconds() / 60
    return gecen, f"{son['created_at']} ({gecen:.0f} dk once, {son['event']})", ts


def tetikle(tok, akis):
    """workflow_dispatch cagirir; 204 -> True."""
    try:
        kod, _ = api(tok, f"/repos/{REPO}/actions/workflows/{akis}.yml/dispatches",
                     "POST", {"ref": "main"})
    except urllib.error.HTTPError as e:
        kod = e.code
    return kod == 204, kod


def main() -> int:
    try:
        tok = token()
    except SystemExit as e:
        print(str(e))
        return 1

    # akis -> gecikme esigi dk (hafta ici)
    ESIK = {
        "veri-cek": 45,
        "altin-cek": 75,
        "kripto-cek": 180,
        "ek-veri-cek": 360,
    }
    # Yalnizca hafta ici calisanlar
    HAFTA_ICI = {"veri-cek", "ek-veri-cek"}

    try:
        _, wf = api(tok, f"/repos/{REPO}/actions/workflows?per_page=100")
        durumlar = {w["name"]: w.get("state") for w in (wf.get("workflows") or [])}
    except urllib.error.HTTPError as e:
        print(f"FAIL workflow listesi: HTTP {e.code}")
        return 1

    simdi = dt.datetime.now(dt.timezone.utc)
    tr = simdi.astimezone(TR)
    hafta_ici = tr.weekday() < 5          # 0=Pzt ... 4=Cum
    # BIST seansi TR 09:30 - 19:00
    seans_ici = hafta_ici and (dt.time(9, 30) <= tr.time() <= dt.time(19, 0))

    hatalar = []      # stdout -> Telegram
    kayitlar = []     # log dosyasi

    for akis, esik in ESIK.items():
        # --- zaman penceresi kurallari ---
        if akis in HAFTA_ICI and not seans_ici:
            continue  # hafta sonu / seans disi -> sessiz kal
        if akis == "altin-cek" and not hafta_ici:
            esik = 180  # hafta sonu: altin Cmt kapali, Pazar gece aciliyor

        st = durumlar.get(akis)
        if st and st != "active":
            kayitlar.append(f"{akis}: DURUM {st} (tetiklenemez)")
            continue
        try:
            gecen, son_metin, _ = son_calisma(tok, akis)
        except urllib.error.HTTPError as e:
            hatalar.append(f"FAIL {akis}: API hata {e.code}")
            continue

        if gecen > esik:
            ok, kod = tetikle(tok, akis)
            if ok:
                kayitlar.append(f"{akis}: TETIKLENDI (son {son_metin}, esik {esik} dk)")
            else:
                hatalar.append(f"FAIL {akis}: tetik basarisiz HTTP {kod} (son {son_metin})")

    # --- 3) Kapanis garantisi: hafta ici TR 18:35-18:59 ---
    kapanis_pencere = hafta_ici and (dt.time(18, 35) <= tr.time() <= dt.time(18, 59))
    if kapanis_pencere:
        try:
            _, son_metin, son_ts = son_calisma(tok, "veri-cek")
            bugun_1830 = dt.datetime.combine(tr.date(), dt.time(18, 30), tzinfo=TR)
            kapanis_var = son_ts is not None and son_ts.astimezone(TR) >= bugun_1830
            if not kapanis_var:
                ok, kod = tetikle(tok, "veri-cek")
                if ok:
                    kayitlar.append(f"veri-cek: KAPANIS GARANTISI tetiklendi (son {son_metin})")
                else:
                    hatalar.append(f"FAIL veri-cek kapanis garantisi: HTTP {kod}")
            else:
                kayitlar.append(f"veri-cek: kapanis calismasi var (son {son_metin})")
        except urllib.error.HTTPError as e:
            hatalar.append(f"FAIL veri-cek kapanis kontrolu: HTTP {e.code}")

    # --- yazim: detay -> log, sadece hatalar -> stdout ---
    if kayitlar:
        baslik = (f"bist-panel harici tetik — {simdi.strftime('%Y-%m-%d %H:%M UTC')} "
                  f"(TR {tr.strftime('%Y-%m-%d %H:%M')}, hafta_ici={hafta_ici}, "
                  f"seans_ici={seans_ici})")
        log_yaz([baslik] + [" - " + s for s in kayitlar])

    for h in hatalar:
        print(h)
    return 1 if hatalar else 0


if __name__ == "__main__":
    sys.exit(main())
