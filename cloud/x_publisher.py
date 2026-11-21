"""Resmi X API v2 (OAuth 1.0a) Bulut Yayıncısı ve Make/n8n Webhook Dağıtıcısı."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple
import requests

try:
    from requests_oauthlib import OAuth1  # type: ignore
except ImportError:  # pragma: no cover
    OAuth1 = None

from .schemas import KanalKarari

X_API_TABAN = "https://api.x.com/2"

BUYUK_TEKNOLOJI_HESAPLARI = (
    "videocardz",
    "tomshardware",
    "digitalfoundry",
    "TechPowerUp",
    "webtekno",
    "shiftdeletenet",
    "technopatnet",
)


class XBulutYayinci:
    """Bilgisayar kapalıyken GitHub Actions / Linux bulut ortamından X yayını yapar."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("X_API_KEY", "").strip()
        self.api_secret = os.environ.get("X_API_SECRET", "").strip()
        self.access_token = os.environ.get("X_ACCESS_TOKEN", "").strip()
        self.access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET", "").strip()
        self.webhook_url = os.environ.get("AUTOMATION_WEBHOOK_URL", "").strip()

    @property
    def x_api_hazir_mi(self) -> bool:
        return all([self.api_key, self.api_secret, self.access_token, self.access_token_secret])

    def _oauth(self) -> Any:
        if OAuth1 is not None:
            return OAuth1(
                self.api_key,
                self.api_secret,
                self.access_token,
                self.access_token_secret,
            )
        return self._stdlib_oauth_imzala

    def _stdlib_oauth_imzala(self, req: requests.PreparedRequest) -> requests.PreparedRequest:
        parsed = urllib.parse.urlsplit(req.url or "")
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        oauth_params = {
            "oauth_consumer_key": self.api_key,
            "oauth_nonce": secrets.token_hex(16),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self.access_token,
            "oauth_version": "1.0",
        }
        tum_param = sorted(query_params + list(oauth_params.items()))
        encoded_params = "&".join(
            f"{urllib.parse.quote(str(k), safe='~')}={urllib.parse.quote(str(v), safe='~')}"
            for k, v in tum_param
        )
        base_str = "&".join(
            [
                (req.method or "GET").upper(),
                urllib.parse.quote(base_url, safe="~"),
                urllib.parse.quote(encoded_params, safe="~"),
            ]
        )
        signing_key = (
            f"{urllib.parse.quote(self.api_secret, safe='~')}&"
            f"{urllib.parse.quote(self.access_token_secret, safe='~')}"
        )
        imza = base64.b64encode(
            hmac.new(signing_key.encode("utf-8"), base_str.encode("utf-8"), hashlib.sha1).digest()
        ).decode("ascii")
        oauth_params["oauth_signature"] = imza
        header_degeri = "OAuth " + ", ".join(
            f'{urllib.parse.quote(k, safe="~")}="{urllib.parse.quote(v, safe="~")}"'
            for k, v in sorted(oauth_params.items())
        )
        req.headers["Authorization"] = header_degeri
        return req

    def getir_profil_bilgisi(self) -> Tuple[Optional[str], Optional[int]]:
        """Aktif X hesabının user_id ve güncel takipçi sayısını döndürür."""
        if not self.x_api_hazir_mi:
            return None, None
        try:
            resp = requests.get(
                f"{X_API_TABAN}/users/me",
                params={"user.fields": "public_metrics,username"},
                auth=self._oauth(),
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                takipci = data.get("public_metrics", {}).get("followers_count")
                return data.get("id"), (int(takipci) if takipci is not None else None)
        except Exception:
            pass
        return None, None

    def ara_hedef_tweetler_1630(self) -> List[Dict[str, str]]:
        """X API Basic/okuma izni varsa büyük teknoloji hesaplarının son paylaşımlarını çeker.
        Free (yalnızca yazma) katmanında 403 dönerse sessizce boş liste döndürür.
        """
        if not self.x_api_hazir_mi:
            return []
        sorgu = "(" + " OR ".join(f"from:{h}" for h in BUYUK_TEKNOLOJI_HESAPLARI) + ") -is:retweet"
        try:
            resp = requests.get(
                f"{X_API_TABAN}/tweets/search/recent",
                params={"query": sorgu, "max_results": 10, "tweet.fields": "created_at,public_metrics"},
                auth=self._oauth(),
                timeout=12,
            )
            if resp.status_code == 200:
                return [
                    {"id": t["id"], "text": t.get("text", "")[:240]}
                    for t in resp.json().get("data", [])
                    if t.get("id")
                ]
        except Exception:
            pass
        return []

    def _gonder_tek_tweet(self, payload: Dict[str, Any]) -> str:
        resp = requests.post(
            f"{X_API_TABAN}/tweets",
            json=payload,
            auth=self._oauth(),
            timeout=20,
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"X API hata kodu {resp.status_code}: {resp.text[:300]}")
        tweet_id = resp.json().get("data", {}).get("id")
        if not tweet_id:
            raise RuntimeError(f"X API yanıtında tweet ID bulunamadı: {resp.text[:200]}")
        return str(tweet_id)

    def yayinla(self, karar: KanalKarari, ilk_yanit_bekleme_sn: int = 120, dry_run: bool = False) -> List[str]:
        """Karar nesnesini X API v2 ve/veya Webhook üzerinden uygular."""
        yayinlanan_idler: List[str] = []

        if dry_run:
            return ["DRY_RUN_ID_1"]

        if self.x_api_hazir_mi:
            if karar.aksiyon_tipi == "anket":
                payload: Dict[str, Any] = {
                    "text": karar.ana_tweetler[0],
                    "poll": {
                        "options": karar.anket_secenekleri,
                        "duration_minutes": 1440,
                    },
                }
                ilk_id = self._gonder_tek_tweet(payload)
                yayinlanan_idler.append(ilk_id)

            elif karar.aksiyon_tipi == "alinti" and karar.hedef_tweet_id:
                payload = {
                    "text": karar.ana_tweetler[0],
                    "quote_tweet_id": karar.hedef_tweet_id,
                }
                ilk_id = self._gonder_tek_tweet(payload)
                yayinlanan_idler.append(ilk_id)

            elif karar.aksiyon_tipi == "yanit" and karar.hedef_tweet_id:
                payload = {
                    "text": karar.ana_tweetler[0],
                    "reply": {"in_reply_to_tweet_id": karar.hedef_tweet_id},
                }
                ilk_id = self._gonder_tek_tweet(payload)
                yayinlanan_idler.append(ilk_id)

            else:
                onceki_id: Optional[str] = None
                for metin in karar.ana_tweetler:
                    payload = {"text": metin}
                    if onceki_id:
                        payload["reply"] = {"in_reply_to_tweet_id": onceki_id}
                    yeni_id = self._gonder_tek_tweet(payload)
                    yayinlanan_idler.append(yeni_id)
                    onceki_id = yeni_id
                    if len(karar.ana_tweetler) > 1:
                        time.sleep(2)

            if karar.ilk_yanit_metni and karar.ilk_yanit_metni.strip() and yayinlanan_idler:
                if ilk_yanit_bekleme_sn > 0:
                    time.sleep(ilk_yanit_bekleme_sn)
                yanit_id = self._gonder_tek_tweet(
                    {
                        "text": karar.ilk_yanit_metni.strip()[:270],
                        "reply": {"in_reply_to_tweet_id": yayinlanan_idler[0]},
                    }
                )
                yayinlanan_idler.append(yanit_id)

        if self.webhook_url:
            requests.post(
                self.webhook_url,
                json=karar.model_dump(mode="json"),
                timeout=15,
            )

        return yayinlanan_idler
