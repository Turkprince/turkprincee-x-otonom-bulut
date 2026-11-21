"""@turkprincee 7/24 Bulut Otonom Orkestratörü (GitHub Actions / Cron / Make / n8n)."""

from __future__ import annotations

import argparse
import html
import json
import os
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any, Dict, List

KOK_DIZIN = Path(__file__).resolve().parent.parent
HAFIZA_YOLU = KOK_DIZIN / "kanal_hafiza.json"
DURUM_YOLU = KOK_DIZIN / "docs" / "status.json"
RSS_YOLU = KOK_DIZIN / "docs" / "rss.xml"

TSI = timezone(timedelta(hours=3))

DILIMLER = (
    "01:30",
    "08:15",
    "09:30",
    "11:20",
    "13:00",
    "15:00",
    "16:30",
    "18:30",
    "20:30",
    "23:15",
)


def belirle_aktif_dilim(simdi_tsi: datetime) -> str:
    """Mevcut TSİ saatine en yakın aktif 24 saatlik yayın dilimini seçer."""
    dakika_toplam = simdi_tsi.hour * 60 + simdi_tsi.minute
    hedefler = {
        "01:30": 1 * 60 + 30,
        "08:15": 8 * 60 + 15,
        "09:30": 9 * 60 + 30,
        "11:20": 11 * 60 + 20,
        "13:00": 13 * 60,
        "15:00": 15 * 60,
        "16:30": 16 * 60 + 30,
        "18:30": 18 * 60 + 30,
        "20:30": 20 * 60 + 30,
        "23:15": 23 * 60 + 15,
    }
    return min(hedefler.keys(), key=lambda k: abs(dakika_toplam - hedefler[k]))


def yukle_hafiza(yol: Path = HAFIZA_YOLU) -> Dict[str, Any]:
    if not yol.exists():
        return {
            "kanal": {
                "handle": "@turkprincee",
                "url": "https://x.com/turkprincee",
                "gorunen_ad": "Donanım & Oyun Lab",
                "son_takipci_sayisi": 21,
                "aktif_faz": 1,
            },
            "acik_dongu_kuyrugu": [],
            "son_14_gun_konu_hafizasi": [],
        }
    return json.loads(yol.read_text(encoding="utf-8"))


def bu_dilim_zaten_yayinlandi_mi(hafiza: Dict[str, Any], bugun_str: str, dilim: str) -> bool:
    """Hem PC hem Bulut açıksa aynı dilimde çift tweet atılmasını engeller."""
    for kayit in reversed(hafiza.get("son_14_gun_konu_hafizasi", [])):
        tarih_tsi = str(kayit.get("tarih_tsi", ""))
        kayit_dilim = str(kayit.get("dilim", ""))
        if tarih_tsi.startswith(bugun_str) and kayit_dilim.startswith(dilim):
            return True
    return False


def temizle_eski_hafiza(kayitlar: List[Dict[str, Any]], simdi_tsi: datetime) -> List[Dict[str, Any]]:
    sinir = simdi_tsi - timedelta(days=14)
    kalanlar: List[Dict[str, Any]] = []
    for k in kayitlar:
        try:
            dt = datetime.fromisoformat(str(k.get("tarih_tsi")))
            if dt >= sinir:
                kalanlar.append(k)
        except Exception:
            kalanlar.append(k)
    return kalanlar


def yaz_durum_paneli(hafiza: Dict[str, Any], son_durum: str) -> None:
    DURUM_YOLU.parent.mkdir(parents=True, exist_ok=True)
    simdi_tsi = datetime.now(TSI).isoformat(timespec="seconds")
    kanal = hafiza.get("kanal", {})
    veri = {
        "guncellenme_tsi": simdi_tsi,
        "durum": son_durum,
        "handle": kanal.get("handle", "@turkprincee"),
        "gorunen_ad": kanal.get("gorunen_ad", "Donanım & Oyun Lab"),
        "takipci": kanal.get("son_takipci_sayisi", 21),
        "aktif_faz": kanal.get("aktif_faz", 1),
        "sabitlenmis_tweet_id": kanal.get("sabitlenmis_flood_ilk_tweet_id"),
        "bekleyen_acik_donguler": [
            d for d in hafiza.get("acik_dongu_kuyrugu", []) if not d.get("tamamlandi", False)
        ],
        "son_yayinlar": list(reversed(hafiza.get("son_14_gun_konu_hafizasi", [])[-10:])),
    }
    DURUM_YOLU.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
    yaz_rss_akisi(hafiza)


def yaz_rss_akisi(hafiza: Dict[str, Any]) -> None:
    """Ücretsiz Buffer / Make / IFTTT entegrasyonları için standart RSS 2.0 akışı üretir."""
    RSS_YOLU.parent.mkdir(parents=True, exist_ok=True)
    simdi_rfc = format_datetime(datetime.now(TSI))
    items_xml: List[str] = []
    for idx, k in enumerate(reversed(hafiza.get("son_14_gun_konu_hafizasi", [])[-20:])):
        ana_liste = k.get("ana_tweetler") or []
        metin = ana_liste[0] if ana_liste else str(k.get("konu_ozeti", ""))
        guid = (k.get("tweet_idleri") or [f"local-{idx}"])[0]
        try:
            pub_dt = format_datetime(datetime.fromisoformat(str(k.get("tarih_tsi"))))
        except Exception:
            pub_dt = simdi_rfc
        items_xml.append(
            "    <item>\n"
            f"      <title>{html.escape(metin[:270])}</title>\n"
            f"      <description>{html.escape(metin)}</description>\n"
            f"      <guid isPermaLink=\"false\">{html.escape(str(guid))}</guid>\n"
            f"      <pubDate>{pub_dt}</pubDate>\n"
            "    </item>"
        )
    rss_icerik = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        "    <title>Donanım &amp; Oyun Lab (@turkprincee) Otonom Yayın Akışı</title>\n"
        "    <link>https://turkprince.github.io/turkprincee-x-otonom-bulut/</link>\n"
        "    <description>7/24 Ücretsiz Bulut Otonom Teknoloji, Donanım ve Oyun Analizleri</description>\n"
        f"    <lastBuildDate>{simdi_rfc}</lastBuildDate>\n"
        + "\n".join(items_xml)
        + "\n  </channel>\n</rss>\n"
    )
    RSS_YOLU.write_text(rss_icerik, encoding="utf-8")


def _yaz_github_ozeti(markdown_metin: str) -> None:
    ozet_dosyasi = os.environ.get("GITHUB_STEP_SUMMARY")
    if ozet_dosyasi:
        with open(ozet_dosyasi, "a", encoding="utf-8") as f:
            f.write(markdown_metin + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="@turkprincee 7/24 Bulut Otonom Kanal Motoru")
    parser.add_argument("--slot", default="auto", help="09:30 | 13:00 | 16:30 | 20:30 | 23:15 | auto")
    parser.add_argument("--no-wait", action="store_true", help="3-14 dk rastgele beklemeyi atla (test/manuel)")
    parser.add_argument("--dry-run", action="store_true", help="X'e göndermeden yalnız karar üret ve doğrula")
    parser.add_argument("--json-only", action="store_true", help="Yalnız yürütülebilir JSON çıktısı bas (Make/n8n)")
    args = parser.parse_args()

    from .rss_radar import topla_guncel_basliklar
    from .schemas import hesapla_aktif_faz
    from .x_publisher import XBulutYayinci

    simdi_tsi = datetime.now(TSI)
    bugun_str = simdi_tsi.strftime("%Y-%m-%d")
    dilim = belirle_aktif_dilim(simdi_tsi) if args.slot == "auto" else args.slot

    hafiza = yukle_hafiza()

    # Ön kontrol: Yalnız ücretsiz GEMINI_API_KEY bile yeterli (0 TL bulut üretimi + RSS/Panel)
    gemini_var = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    yayinci = XBulutYayinci()

    if not gemini_var:
        mesaj = (
            "### ⏳ Bulut Kurulumu Bekleniyor (`@turkprincee`)\n"
            f"- **Kontrol Zamanı (TSİ):** `{simdi_tsi.isoformat(timespec='seconds')}`\n"
            f"- **`GEMINI_API_KEY` (Ücretsiz) tanımlı mı?** `HAYIR`\n\n"
            "GitHub deponuzun **Settings → Secrets and variables → Actions** bölümüne `GEMINI_API_KEY` eklediğiniz anda "
            "otomatik bulut üretimi ve RSS akışı başlayacaktır."
        )
        if not args.json_only:
            print(mesaj)
        _yaz_github_ozeti(mesaj)
        yaz_durum_paneli(hafiza, "API anahtarı bekleniyor (Hazır)")
        return 0

    if not args.dry_run and bu_dilim_zaten_yayinlandi_mi(hafiza, bugun_str, dilim):
        bilgi = f"[ATLANDI] {bugun_str} {dilim} dilimi zaten yayınlanmış (çift paylaşım koruması)."
        if not args.json_only:
            print(bilgi)
        _yaz_github_ozeti(f"### ✅ Çift Paylaşım Koruması\n`{bilgi}`")
        return 0

    # Canlı takipçi sayısını ve otomatik faz geçişini güncelle
    _, canli_takipci = yayinci.getir_profil_bilgisi()
    if canli_takipci is not None:
        hafiza.setdefault("kanal", {})["son_takipci_sayisi"] = canli_takipci
    mevcut_takipci = int(hafiza.get("kanal", {}).get("son_takipci_sayisi", 21))
    hafiza.setdefault("kanal", {})["aktif_faz"] = hesapla_aktif_faz(mevcut_takipci)

    from .gemini_brain import uret_kanal_karari

    bekleme_dk = secrets.randbelow(12) + 3
    rss_basliklari = topla_guncel_basliklar()
    aday_tweetler = yayinci.ara_hedef_tweetler_1630() if dilim == "16:30" else []

    karar = uret_kanal_karari(
        dilim=dilim,
        hafiza=hafiza,
        rss_basliklari=rss_basliklari,
        aday_hedef_tweetler=aday_tweetler,
        zorunlu_bekleme_dakika=bekleme_dk,
    )

    if args.json_only:
        print(json.dumps(karar.model_dump(mode="json"), ensure_ascii=False))
        return 0

    if not args.no_wait and not args.dry_run:
        print(f"[SPAM KORUMASI] Hedef saatten +{karar.bekleme_dakika} dakika rastgele sapma bekleniyor...")
        time.sleep(karar.bekleme_dakika * 60)

    tweet_idleri = yayinci.yayinla(
        karar=karar,
        ilk_yanit_bekleme_sn=(0 if args.no_wait else 120),
        dry_run=args.dry_run,
    )

    yayin_zamani = datetime.now(TSI)
    if not args.dry_run:
        # 09:30 diliminde bekleyen açık döngüleri tamamlandı işaretle
        if dilim == "09:30":
            for d in hafiza.get("acik_dongu_kuyrugu", []):
                if not d.get("tamamlandi", False):
                    d["tamamlandi"] = True

        # 23:15 diliminde yarın sabah 09:30 için yeni açık döngü kaydı ekle
        if dilim == "23:15":
            yarin = (yayin_zamani + timedelta(days=1)).strftime("%Y-%m-%d")
            hafiza.setdefault("acik_dongu_kuyrugu", []).append(
                {
                    "hedef_tarih": yarin,
                    "hedef_dilim": "09:30",
                    "soz_verilen_konu": karar.hafiza_ozeti,
                    "kaynak_tweet_id": tweet_idleri[0] if tweet_idleri else None,
                    "tamamlandi": False,
                }
            )

        yeni_kayit = {
            "tarih_tsi": yayin_zamani.isoformat(timespec="seconds"),
            "dilim": dilim,
            "aksiyon_tipi": karar.aksiyon_tipi,
            "tweet_idleri": tweet_idleri,
            "ana_tweetler": karar.ana_tweetler,
            "anket_secenekleri": karar.anket_secenekleri,
            "konu_ozeti": karar.hafiza_ozeti,
            "gelir_aksiyonu_var_mi": karar.gelir_aksiyonu_var_mi,
        }
        mevcut_liste = hafiza.get("son_14_gun_konu_hafizasi", [])
        mevcut_liste.append(yeni_kayit)
        hafiza["son_14_gun_konu_hafizasi"] = temizle_eski_hafiza(mevcut_liste, yayin_zamani)
        HAFIZA_YOLU.write_text(json.dumps(hafiza, ensure_ascii=False, indent=2), encoding="utf-8")
        yaz_durum_paneli(hafiza, f"Aktif — Son yayın: {dilim} ({karar.aksiyon_tipi})")

    ozet = (
        f"### 🚀 Otonom Yayın Tamamlandı (`{dilim} TSİ`)\n"
        f"- **Aktif Faz:** `FAZ {karar.aktif_faz}` (`{mevcut_takipci}` takipçi)\n"
        f"- **Aksiyon Tipi:** `{karar.aksiyon_tipi}` (+{karar.bekleme_dakika} dk sapma)\n"
        f"- **Yayınlanan Tweet ID:** `{', '.join(tweet_idleri)}`\n"
        f"- **Konu Özeti:** {karar.hafiza_ozeti}\n"
    )
    print(ozet)
    _yaz_github_ozeti(ozet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
