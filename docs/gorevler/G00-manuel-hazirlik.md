# G00 — Manuel hazırlık (ajan değil, sen yapacaksın)

Bu adımda LLM kullanılmıyor, token harcanmıyor. Sunucuda, terminalde yapılıyor.

## 1. Yamaları uygula
```bash
cd ~/bist-panel            # repo yolun neyse
git checkout main && git pull
git am 0001-*.patch        # P0 düzeltmeleri + sinyal_denetim.py + testler
git am 0002-*.patch        # AGENTS.md + docs/gorevler + docs/analiz
pip install pytest pandas numpy
python3 -m pytest tests -q # 6 passed görmelisin
git push
```

## 2. Hermes ayarları (`~/.hermes/config.yaml`)
```yaml
providers:
  deepseek:                       # `hermes config show` çıktısındaki model.provider değeri
    request_timeout_seconds: 120
    stale_timeout_seconds: 180
```
Ardından:
- `hermes fallback` ile ücretsiz bir yedek sağlayıcı ekle (Gemini AI Studio veya OpenRouter `:free`).
- `hermes doctor` ile bağlantıyı test et.

## 3. Hermes'i repo klasöründe başlat
`AGENTS.md` sadece Hermes'in **çalışma dizini** repo kökü olduğunda otomatik yüklenir.
- Gateway kullanıyorsan çalışma dizinini repo kökü olarak ayarla.
- Ya da ilk mesajında `cd ~/bist-panel` yaptır.
