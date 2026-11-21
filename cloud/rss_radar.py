"""Sıfır API anahtarıyla küresel ve yerel teknoloji/donanım/oyun RSS gündem radarı."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from typing import Dict, List
import requests

RSS_KAYNAKLARI: Dict[str, str] = {
    "VideoCardz": "https://videocardz.com/feed",
    "TechPowerUp": "https://www.techpowerup.com/rss/news",
    "TomsHardware": "https://www.tomshardware.com/feeds/all",
    "PCGamer": "https://www.pcgamer.com/rss/",
    "Eurogamer": "https://www.eurogamer.net/feed/news",
    "Technopat": "https://www.technopat.net/feed/",
    "Webtekno": "https://www.webtekno.com/rss.xml",
    "ShiftDelete": "https://shiftdelete.net/feed",
}

TAG_SIL = re.compile(r"<[^>]+>")


def _temizle(metin: str, limit: int = 200) -> str:
    temiz = html.unescape(TAG_SIL.sub(" ", metin or ""))
    temiz = re.sub(r"\s+", " ", temiz).strip()
    return temiz[:limit]


def topla_guncel_basliklar(kaynak_basi_limit: int = 4, timeout_sn: int = 8) -> List[Dict[str, str]]:
    """RSS kaynaklarından son başlıkları çeker; hata veren kaynağı sessizce atlar."""
    sonuclar: List[Dict[str, str]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DonanimOyunLabBot/1.0; +https://x.com/turkprincee)"
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
                if baslik.strip():
                    sonuclar.append(
                        {
                            "kaynak": kaynak,
                            "baslik": _temizle(baslik, 140),
                            "ozet": _temizle(ozet, 220),
                            "tarih": _temizle(tarih, 40),
                        }
                    )
        except Exception:
            continue
    return sonuclar
