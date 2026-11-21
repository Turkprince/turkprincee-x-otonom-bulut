# @turkprincee (Donanım & Oyun Lab) — 7/24 Sıfır Maliyetli Bulut Sistemi

Bu sistem, **bilgisayarınız tamamen kapalıyken dahi** her gün **TSİ 09:30, 13:00, 16:30, 20:30 ve 23:15** dilimlerinde (+3–14 dk rastgele sapma ile) GitHub'ın bulut sunucuları (`GitHub Actions`) üzerinde çalışarak `@turkprincee` kanalını yönetir, 14 günlük konu hafızasını korur ve takipçi eşiklerine göre (`3.000` FAZ 2, `10.000` FAZ 3) otomatik faz geçişi yapar.

---

## Mimari Özeti (Bilgisayar Açık veya Kapalıyken Kesintisiz Devam)
1. **Zamanlayıcı (`GitHub Actions Cron`):** Günde 5 kez Ubuntu Linux bulut sunucusunu otomatik uyandırır (aylık ~225 dk kullanım; GitHub ücretsiz kotası olan 2.000 dk/ay sınırının %12'sinden azdır — **0 TL/ay**).
2. **Gündem Radarı (`cloud/rss_radar.py` + Google Search):** VideoCardz, Tom's Hardware, TechPowerUp, PC Gamer, Eurogamer, Technopat, Webtekno ve ShiftDelete RSS akışlarını + Google Search verisini anlık tarar.
3. **Editör Beyni (`cloud/gemini_brain.py`):** `gemini-3.8-flash` modeli ve `KanalKarari` Pydantic doğrulayıcısı ile 270 karakter, 0 hashtag, 0 URL, 0 yapay zekâ klişesi ve 14 günlük konu tekrarsızlığı kurallarını zorunlu tutar.
4. **Resmi Bulut Yayıncısı (`cloud/x_publisher.py`):** Resmi X API v2 (OAuth 1.0a — ücretsiz katmanda aylık 500–1.500 tweet yazma hakkı) ve/veya Make.com / n8n Webhook üzerinden tek tweet, numaralandırılmış flood, X anketi ve 2 dakika gecikmeli ilk yanıtı yayınlar.
5. **Çift Paylaşım Koruması:** Hem bilgisayarınız hem bulut aynı anda aktif olsa bile `kanal_hafiza.json` dilim kilidi sayesinde aynı dilimde asla mükerrer tweet atılmaz.
6. **Canlı Bulut Durum Sitesi (`docs/index.html`):** GitHub Pages üzerinden telefonunuzdan veya tarayıcıdan kanalın aktif fazını, son yayınlarını ve açık döngü kuyruğunu canlı gösterir.

---

## Bulutu Aktifleştirmek İçin Tek Seferlik 5 Anahtar (3 Dakika)

Bulut deposu GitHub hesabınıza (`Turkprince/turkprincee-x-otonom-bulut`) özel (private) olarak yüklenmiştir. Bilgisayar kapalıyken X'e yazabilmesi için GitHub deponuzda **Settings → Secrets and variables → Actions → New repository secret** ekranından şu 5 anahtarı eklemeniz yeterlidir:

| Secret Adı | Nereden Alınır? |
|---|---|
| `GEMINI_API_KEY` | [Google AI Studio API Key](https://aistudio.google.com/apikey) (Ücretsiz) |
| `X_API_KEY` | [X Developer Portal](https://developer.x.com/en/portal/dashboard) → App Settings → Keys and tokens → Consumer Key *(App permissions: **Read and Write** seçili olmalı)* |
| `X_API_SECRET` | Consumer Secret (API Key Secret) |
| `X_ACCESS_TOKEN` | Authentication Tokens → Access Token and Secret *(Read and Write iznini açtıktan sonra üretin)* |
| `X_ACCESS_TOKEN_SECRET` | Access Token Secret |

> **Opsiyonel (Make.com / n8n kullananlar için):** `AUTOMATION_WEBHOOK_URL` secret'ını eklerseniz motor her dilimde ürettiği yürütülebilir JSON karar çıktısını doğrudan Make/n8n senaryonuza da gönderir. Hazır şablon: `otomasyon/n8n_make_blueprint.json`.

---

## Bulut Durum Sitesini (GitHub Pages) Açma (Opsiyonel)
Deponuzda **Settings → Pages → Source: Deploy from a branch → Branch: `main` / `/docs`** seçip kaydettiğinizde 7/24 canlı durum siteniz yayına girer.

## Manuel Test Komutları
```bash
pip install -r requirements.txt
# X'e göndermeden test / JSON çıktısı doğrulama:
python -m cloud.run_slot --slot 09:30 --dry-run --no-wait
# Yalnız Make/n8n uyumlu saf JSON çıktısı alma:
python -m cloud.run_slot --slot 20:30 --json-only
```
