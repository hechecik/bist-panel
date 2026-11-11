#!/usr/bin/env python3
"""bist-panel harici tetikleyici — cron-job.org yerine.

Neden: GitHub'in kendi `schedule` mekanizmasi bu repoda fiilen tetiklenmiyor.
cron-job.org hesabi/kimligi yok; fine-grained PAT de paneldan elle uretilmeli.
Elimizdeki token `workflow` scope'lu ve workflow_dispatch cagirabiliyor (204).

Bu script: zamanlanmis is akislarindan gecikmis olani workflow_dispatch ile tetikler.
Cikti: yalnizca GERCEK bir aksiyon alindiginda satir basar (sessiz watchdog deseni).

Token: koda YAZILMAZ. Once ortam degiskeni (GITHUB_TOKEN / GH_TOKEN), yoksa
~/.git-credentials dosyasindan okunur.
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
    raise SystemExit("token bulunamadi: GITHUB_TOKEN/GH_TOKEN veya ~/.git-credentials")


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


def main() -> int:
    tok = token()

    # akis -> gecikme esigi dk (hafta ici)
    ESIK = {
        "veri-cek": 45,
        "altin-cek": 75,
        "kripto-cek": 75,
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

    tetiklenen = []
    satirlar = []

    for akis, esik in ESIK.items():
        # --- zaman penceresi kurallari ---
        if akis in HAFTA_ICI and not seans_ici:
            continue  # hafta sonu / seans disi -> sessiz kal
        if akis == "altin-cek" and not hafta_ici:
            esik = 180  # hafta sonu: altin Cmt kapali, Pazar gece aciliyor

        st = durumlar.get(akis)
        if st and st != "active":
            satirlar.append(f"{akis}: DURUM {st} (tetiklenemez)")
            continue
        try:
            _, d = api(tok, f"/repos/{REPO}/actions/workflows/{akis}.yml/runs?per_page=1&branch=main")
            kosular = d.get("workflow_runs") or []
        except urllib.error.HTTPError as e:
            satirlar.append(f"{akis}: API hata {e.code}")
            continue

        if not kosular:
            gecen = 10**6
            son_metin = "hic calisma yok"
        else:
            son = kosular[0]
            ts = dt.datetime.fromisoformat(son["created_at"].replace("Z", "+00:00"))
            gecen = (simdi - ts).total_seconds() / 60
            son_metin = f"{son['created_at']} ({gecen:.0f} dk once, {son['event']})"

        if gecen > esik:
            try:
                kod, _ = api(tok, f"/repos/{REPO}/actions/workflows/{akis}.yml/dispatches",
                             "POST", {"ref": "main"})
            except urllib.error.HTTPError as e:
                kod = e.code
            if kod == 204:
                tetiklenen.append(akis)
                satirlar.append(f"{akis}: TETIKLENDI (son {son_metin}, esik {esik} dk)")
            else:
                satirlar.append(f"{akis}: TETIK BASARISIZ HTTP {kod} (son {son_metin})")
        # gecikme yoksa satir basma (sessiz)

    if not satirlar:
        return 0

    print(f"bist-panel harici tetik — {simdi.strftime('%Y-%m-%d %H:%M UTC')} "
          f"(TR {tr.strftime('%Y-%m-%d %H:%M')}, hafta_ici={hafta_ici}, seans_ici={seans_ici})")
    for s in satirlar:
        print(" - " + s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
