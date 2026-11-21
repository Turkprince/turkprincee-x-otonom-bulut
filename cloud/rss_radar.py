"""Sıfır API anahtarıyla 24 saat dinamik küresel & yerel teknoloji/donanım/oyun RSS radarı ve etki puanlayıcısı."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List
import requests

RSS_KAYNAKLARI: Dict[str, str] = {
    "VideoCardz": "https://videocardz.com/feed",
    "TechPowerUp": "https://www.techpowerup.com/rss/news",
    "TomsHardware": "https://www.tomshardware.com/feeds/all",
    "Wccftech": "https://wccftech.com/feed/",
    "PCGamer": "https://www.pcgamer.com/rss/",
    "Eurogamer": "https://www.eurogamer.net/feed/news",
    "Technopat": "https://www.technopat.net/feed/",
    "Webtekno": "https://www.webtekno.com/rss.xml",
    "ShiftDelete": "https://shiftdelete.net/feed",
    "DonanimHaber": "https://www.donanimhaber.com/rss/tum/",
}

KRITIK_ANAHTARLAR = (
    "hotfix",
    "driver",
    "sürücü",
    "rtx",
    "radeon",
    "ryzen",
    "zen 6",
    "core ultra",
    "oled",
    "qd-oled",
    "woled",
    "vram",
    "dlss",
    "fsr",
    "gta",
    "ps5",
    "xbox",
    "switch 2",
    "steam",
    "ssd",
    "nvme",
    "ddr5",
    "ddr6",
    "wi-fi",
    "benchmark",
    "leak",
    "sızıntı",
    "fiyat",
    "indirim",
    "bug",
    "hata",
)

TAG_SIL = re.compile(r"<[^>]+>")


def _temizle(metin: str, limit: int = 200) -> str:
    temiz = html.unescape(TAG_SIL.sub(" ", metin or ""))
    temiz = re.sub(r"\s+", " ", temiz).strip()
    return temiz[:limit]


def _hesapla_etki_skoru(baslik: str, ozet: str) -> int:
    birlesik = f"{baslik} {ozet}".lower()
    skor = 10
    for k in KRITIK_ANAHTARLAR:
        if k in birlesik:
            skor += 15
    if any(rakam in birlesik for rakam in ("%", "fps", "hz", "gb", "ms", "tbw", "nit")):
        skor += 12
    return skor


def topla_guncel_basliklar(kaynak_basi_limit: int = 4, timeout_sn: int = 7) -> List[Dict[str, Any]]:
    """RSS kaynaklarından son başlıkları çeker ve dinamik teknik etki skoruna göre sıralar."""
    sonuclar: List[Dict[str, Any]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DonanimOyunLabBot/2.0; +https://x.com/turkprincee)"
    }
    for kaynak, url in RSS_KAYNAKLARI.items():
        try:
            resp = requests.get(url, headers=headers, timeout=timeout_sn)
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")
            if not items:
                items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for item in items[:kaynak_basi_limit]:
                baslik = (
                    item.findtext("title")
                    or item.findtext("{http://www.w3.org/2005/Atom}title")
                    or ""
                )
                ozet = (
                    item.findtext("description")
                    or item.findtext("{http://www.w3.org/2005/Atom}summary")
                    or ""
                )
                tarih = (
                    item.findtext("pubDate")
                    or item.findtext("{http://www.w3.org/2005/Atom}updated")
                    or ""
                )
                temiz_b = _temizle(baslik, 145)
                temiz_o = _temizle(ozet, 220)
                if temiz_b:
                    sonuclar.append(
                        {
                            "kaynak": kaynak,
                            "baslik": temiz_b,
                            "ozet": temiz_o,
                            "tarih": _temizle(tarih, 40),
                            "etki_skoru": _hesapla_etki_skoru(temiz_b, temiz_o),
                        }
                    )
        except Exception:
            continue
    sonuclar.sort(key=lambda x: int(x.get("etki_skoru", 0)), reverse=True)
    return sonuclar
