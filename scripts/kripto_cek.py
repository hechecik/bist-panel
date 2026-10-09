#!/usr/bin/env python3
"""KRİPTO PANEL — kripto veri çekme scripti (24/7 GitHub Actions).

Anti-hallüsinasyon: TÜM veriler gerçek kaynaklardan çekilir, hiçbiri uydurulmaz.
- Fiyat (USD + TL), 24s / 7g değişim, hacim, piyasa değeri, 7g sparkline: CoinGecko
- Toplam piyasa değeri + BTC dominansı: CoinGecko /global
- Korku & Açgözlülük endeksi: alternative.me/fng
- CoinGecko düşerse fiyat yedeği: Coinbase exchange-rates (sadece USD, sparkline yok)

API key yok, kişisel bilgi yok. Çıktı: data/kripto.json
Skor kuralları koddaki gibi açıkça yazılıdır (kural bazlı, yorum uydurma yok).
"""
import json
import time
import urllib.request
import urllib.error
import datetime as dt
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CIKTI = DATA_DIR / "kripto.json"

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
      "Accept": "application/json"}

# Takip edilen coinler — CoinGecko ID'si
COINLER = [
    "bitcoin", "ethereum", "tether", "binancecoin", "solana", "ripple",
    "usd-coin", "cardano", "dogecoin", "tron", "avalanche-2", "chainlink",
    "polkadot", "toncoin", "shiba-inu", "litecoin", "sui", "near",
    "uniswap", "stellar", "bitcoin-cash", "aptos", "arbitrum", "optimism",
]

FNG_TR = {
    "Extreme Fear": "AŞIRI KORKU", "Fear": "KORKU", "Neutral": "NÖTR",
    "Greed": "AÇGÖZLÜLÜK", "Extreme Greed": "AŞIRI AÇGÖZLÜLÜK",
}

# Momentum skoru hesaplanmayan stablecoinler (dolar paritesi — sinyal anlamsız)
STABLE = {"USDT", "USDC", "DAI", "FDUSD", "TUSD", "USDE", "PYUSD", "USDD"}


def log(msg):
    print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def get_json(url, timeout=25, deneme=3, bekle=2.5):
    """HTTP GET + JSON — 429/geçici hatalarda yeniden dener (CoinGecko rate limit)."""
    son = None
    for i in range(deneme):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            son = e
            if i < deneme - 1:
                time.sleep(bekle * (i + 1))
    raise son


def spark_indir(ham, nokta=30):
    """7 günlük saatlik sparkline → ~30 noktaya indir (JSON'u şişirmemek için)."""
    if not ham:
        return []
    adim = max(1, len(ham) // nokta)
    s = [round(float(x), 6) for x in ham[::adim]]
    if ham and abs(s[-1] - float(ham[-1])) > 1e-9:  # son fiyat mutlaka dahil
        s.append(round(float(ham[-1]), 6))
    return s


def market_cek(vs_currency):
    ids = ",".join(COINLER)
    url = ("https://api.coingecko.com/api/v3/coins/markets?vs_currency=" + vs_currency +
           f"&ids={ids}&order=market_cap_desc&sparkline=true&price_change_percentage=24h,7d")
    return get_json(url)


def kripto_hesapla(usd, try_map, fng):
    """CoinGecko USD + TRY verisini birleştir → coin listesi (skor kural bazlı)."""
    korku = fng.get("deger") if fng else None
    coinler = []
    for c in usd:
        try:
            sembol = (c.get("symbol") or "").upper()
            fiyat = c.get("current_price")
            if not sembol or fiyat is None:
                continue
            d24 = c.get("price_change_percentage_24h")
            d7 = c.get("price_change_percentage_7d_in_currency")
            spark = spark_indir((c.get("sparkline_in_7d") or {}).get("price"))
            # 7g aralık içindeki konum (0 = dip, 1 = zirve) — sparkline'dan
            konum = None
            if len(spark) >= 5:
                lo, hi = min(spark), max(spark)
                if hi > lo:
                    konum = round((spark[-1] - lo) / (hi - lo), 3)
            # ── SKOR: kurallar açık, deterministik (uydurma yorum yok) ──
            if sembol in STABLE:
                skor, nedenler, sinyal = 0, ["Stablecoin (dolar paritesi) — momentum skoru hesaplanmaz"], "PARİTE"
                coinler.append({
                    "sira": c.get("market_cap_rank"), "sembol": sembol, "ad": c.get("name"),
                    "fiyat": fiyat, "fiyat_tl": try_map.get(sembol),
                    "degisim_24s": round(d24, 2) if d24 is not None else None,
                    "degisim_7g": round(d7, 2) if d7 is not None else None,
                    "hacim": c.get("total_volume"), "piyasa_degeri": c.get("market_cap"),
                    "ath_fark": None, "konum_7g": konum, "spark": spark,
                    "skor": skor, "sinyal": sinyal, "nedenler": nedenler,
                })
                continue
            skor, nedenler = 0, []
            if d24 is not None:
                if d24 > 3:
                    skor += 1; nedenler.append(f"24s {d24:+.1f}% → güçlü kısa vade momentum")
                elif d24 < -3:
                    skor -= 1; nedenler.append(f"24s {d24:+.1f}% → satış baskısı")
            if d7 is not None:
                if d7 > 8:
                    skor += 1; nedenler.append(f"7g {d7:+.1f}% → haftalık trend yukarı")
                elif d7 < -8:
                    skor -= 1; nedenler.append(f"7g {d7:+.1f}% → haftalık trend aşağı")
            if konum is not None:
                if konum >= 0.75:
                    skor += 1; nedenler.append(f"Fiyat 7g aralığın üst %25'inde (konum {konum:.2f}) → kırılım bölgesi")
                elif konum <= 0.25:
                    skor -= 1; nedenler.append(f"Fiyat 7g aralığın alt %25'inde (konum {konum:.2f}) → dip bölgesi")
            if korku is not None:
                if korku < 25:
                    skor += 1; nedenler.append(f"Korku endeksi {korku} → aşırı korku, kontra alım")
                elif korku > 75:
                    skor -= 1; nedenler.append(f"Korku endeksi {korku} → aşırı açgözlülük, düzeltme riski")
            sinyal = "AL" if skor >= 2 else ("SAT" if skor <= -2 else "TUT")
            coinler.append({
                "sira": c.get("market_cap_rank"),
                "sembol": sembol,
                "ad": c.get("name"),
                "fiyat": fiyat,
                "fiyat_tl": try_map.get(sembol),
                "degisim_24s": round(d24, 2) if d24 is not None else None,
                "degisim_7g": round(d7, 2) if d7 is not None else None,
                "hacim": c.get("total_volume"),
                "piyasa_degeri": c.get("market_cap"),
                "ath_fark": round(c.get("ath_change_percentage"), 1) if c.get("ath_change_percentage") is not None else None,
                "konum_7g": konum,
                "spark": spark,
                "skor": skor,
                "sinyal": sinyal,
                "nedenler": nedenler[:4],
            })
        except Exception:
            continue
    coinler.sort(key=lambda x: (x["sira"] is None, x["sira"] or 999))
    return coinler


def kripto_cek():
    sonuc = {"uretildi": dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), "kaynak": None}
    usd, try_map, global_d, fng = None, {}, None, None
    try:
        usd = market_cek("usd")
        sonuc["kaynak"] = "coingecko"
        log(f"CoinGecko USD OK: {len(usd)} coin")
    except Exception as e:
        log(f"CoinGecko markets hata: {str(e)[:80]}")
    time.sleep(1.5)  # rate-limit (429) önlemi
    # TRY fiyatlar (Türk kullanıcı için TL karşılığı)
    try:
        for c in market_cek("try"):
            try_map[(c.get("symbol") or "").upper()] = c.get("current_price")
        log(f"CoinGecko TRY OK: {len(try_map)} coin")
    except Exception as e:
        log(f"CoinGecko TRY hata: {str(e)[:60]}")
    time.sleep(1.5)  # rate-limit (429) önlemi
    # Global (toplam piyasa değeri + BTC dominansı)
    # CoinGecko /global sık sık 429 verir → yedek: CoinPaprika /global (API key'siz, güvenilir)
    try:
        g = get_json("https://api.coingecko.com/api/v3/global", deneme=2, bekle=2)["data"]
        global_d = {
            "toplam_piyasa_degeri": g["total_market_cap"]["usd"],
            "toplam_hacim": g["total_volume"]["usd"],
            "degisim_24s": round(g.get("market_cap_change_percentage_24h_usd") or 0, 2),
            "btc_dominans": round((g.get("market_cap_percentage") or {}).get("btc") or 0, 1),
            "eth_dominans": round((g.get("market_cap_percentage") or {}).get("eth") or 0, 1),
            "aktif_coin": g.get("active_cryptocurrencies"),
            "kaynak": "coingecko",
        }
        log(f"Global OK (coingecko): BTC dominans %{global_d['btc_dominans']}")
    except Exception as e:
        log(f"Global coingecko hata: {str(e)[:50]} → coinpaprika deneniyor")
        try:
            p = get_json("https://api.coinpaprika.com/v1/global", deneme=2, bekle=2)
            global_d = {
                "toplam_piyasa_degeri": p.get("market_cap_usd"),
                "toplam_hacim": p.get("volume_24h_usd"),
                "degisim_24s": round(p.get("market_cap_change_24h") or 0, 2),
                "btc_dominans": round(p.get("bitcoin_dominance_percentage") or 0, 1),
                "eth_dominans": None,
                "aktif_coin": p.get("cryptocurrencies_number"),
                "kaynak": "coinpaprika",
            }
            log(f"Global OK (coinpaprika): BTC dominans %{global_d['btc_dominans']}")
        except Exception as e2:
            log(f"Global hata: {str(e2)[:60]}")
    # Korku & Açgözlülük
    try:
        f = get_json("https://api.alternative.me/fng/?limit=2")["data"]
        guncel = f[0]
        onceki = f[1] if len(f) > 1 else None
        fng = {
            "deger": int(guncel.get("value")),
            "etiket": FNG_TR.get(guncel.get("value_classification"), guncel.get("value_classification")),
            "onceki": int(onceki.get("value")) if onceki else None,
        }
        log(f"Korku endeksi OK: {fng['deger']} ({fng['etiket']})")
    except Exception as e:
        log(f"F&G hata: {str(e)[:60]}")
    # YEDEK: CoinGecko komple düşerse → Coinbase fiyatları (sparkline yok, dürüstçe belirtilir)
    if not usd:
        try:
            cb = get_json("https://api.coinbase.com/v2/exchange-rates?currency=USD")["data"]["rates"]
            simge = {"BTC": "BTC", "ETH": "ETH", "USDT": "USDT", "BNB": "BNB", "SOL": "SOL",
                     "XRP": "XRP", "USDC": "USDC", "ADA": "ADA", "DOGE": "DOGE", "TRX": "TRX",
                     "AVAX": "AVAX", "LINK": "LINK", "DOT": "DOT", "TON": "TON", "SHIB": "SHIB",
                     "LTC": "LTC", "SUI": "SUI", "NEAR": "NEAR", "UNI": "UNI", "XLM": "XLM",
                     "BCH": "BCH", "APT": "APT", "ARB": "ARB", "OP": "OP"}
            coinler = []
            for i, (sem, _) in enumerate(simge.items(), 1):
                h = cb.get(sem)
                if not h:
                    continue
                try:
                    f = 1.0 / float(h) if float(h) else None
                except Exception:
                    f = None
                if not f:
                    continue
                coinler.append({"sira": i, "sembol": sem, "ad": sem, "fiyat": round(f, 8),
                                "fiyat_tl": try_map.get(sem), "degisim_24s": None, "degisim_7g": None,
                                "hacim": None, "piyasa_degeri": None, "ath_fark": None,
                                "konum_7g": None, "spark": [], "skor": 0, "sinyal": "TUT",
                                "nedenler": ["Coinbase yedek kaynağı — 24s/7g değişim ve grafik yok"]})
            sonuc["kaynak"] = "coinbase-yedek"
            sonuc["coinler"] = coinler
            sonuc["global"] = global_d
            sonuc["korku"] = fng
            sonuc["not"] = ("CoinGecko erişilemedi, Coinbase yedek fiyatları kullanıldı "
                            "(24s/7g değişim ve grafik yok).")
            log(f"Coinbase yedek OK: {len(coinler)} coin")
            return sonuc
        except Exception as e:
            log(f"Coinbase yedek hata: {str(e)[:60]}")

    coinler = kripto_hesapla(usd or [], try_map, fng)
    sonuc["coinler"] = coinler
    sonuc["global"] = global_d
    sonuc["korku"] = fng
    sonuc["not"] = ("Fiyatlar CoinGecko'dan (USD + TL karşılığı), 7g grafik saatlik sparkline'dan. "
                    "Skor kural bazlıdır: 24s >±3% (±1), 7g >±8% (±1), fiyat 7g aralığın "
                    "üst/alt %25'inde (±1), korku endeksi <25/>75 (±1). Skor ≥2 AL, ≤-2 SAT, "
                    "arası TUT. Kripto 24/7 işlem görür — veri hafta sonu da güncellenir.")
    return sonuc


def main():
    log("=== KRİPTO PANEL veri çekme başladı ===")
    paket = kripto_cek()
    CIKTI.write_text(json.dumps(paket, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"kripto.json yazıldı: {CIKTI.stat().st_size} byte | {len(paket.get('coinler', []))} coin")
    log("=== TAMAM ===")


if __name__ == "__main__":
    main()
