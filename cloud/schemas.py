"""@turkprincee Otonom X Kanal Motoru — Veri Şemaları ve Anayasa Doğrulayıcıları."""

from __future__ import annotations

import re
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator

YASAKLI_KLISELER = (
    "merhaba arkadaşlar",
    "harika bir haber",
    "gelin birlikte inceleyelim",
    "işte detaylar",
    "sizler için derledik",
    "hazırsanız başlayalım",
)

URL_REGEX = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
HASHTAG_REGEX = re.compile(r"(?<!\w)#[A-Za-zÇĞİÖŞÜçğıöşü0-9_]+")
EMOJI_REGEX = re.compile(
    "["
    "\U0001F300-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000027BF"
    "]"
)


def say_emoji(metin: str) -> int:
    return len(EMOJI_REGEX.findall(metin))


def hesapla_aktif_faz(takipci_sayisi: int) -> Literal[1, 2, 3]:
    if takipci_sayisi >= 10_000:
        return 3
    if takipci_sayisi >= 3_000:
        return 2
    return 1


class KanalKarari(BaseModel):
    """Kullanıcı protokolündeki birebir yürütülebilir JSON karar yapısı."""

    aktif_faz: Literal[1, 2, 3] = Field(
        description="Takipçi sayısına göre aktif faz: 1 (0-2999), 2 (3000-9999), 3 (10000+)."
    )
    aksiyon_tipi: Literal["tek_tweet", "flood", "anket", "alinti", "yanit"] = Field(
        description="Zaman dilimine uygun aksiyon tipi."
    )
    bekleme_dakika: int = Field(
        ge=3,
        le=14,
        description="Hedef saatten sonra bot algısını kırmak için beklenecek dakika (3-14).",
    )
    hedef_tweet_id: Optional[str] = Field(
        default=None,
        description="Alıntı veya yanıt aksiyonlarında hedef tweet ID'si; diğerlerinde null.",
    )
    ana_tweetler: List[str] = Field(
        min_length=1,
        max_length=7,
        description="Yayınlanacak ana tweet veya flood dizisi. Her öğe en fazla 270 karakter.",
    )
    anket_secenekleri: List[str] = Field(
        default_factory=list,
        description="Aksiyon tipi 'anket' ise 2-4 adet seçenek (her biri <=25 karakter); değilse boş liste.",
    )
    ilk_yanit_metni: Optional[str] = Field(
        default=None,
        description="Ana tweetten 2 dakika sonra kendi altına atılacak ilk yanıt (FAZ 3 linki veya ek teknik not); gerekmiyorsa null veya boş.",
    )
    gorsel_prompt_en: Optional[str] = Field(
        default=None,
        description="Opsiyonel İngilizce görsel üretim istemi veya null.",
    )
    hafiza_ozeti: str = Field(
        min_length=10,
        description="14 günlük konu tekrarını önlemek için bu paylaşımın teknik konu özeti.",
    )
    gelir_aksiyonu_var_mi: bool = Field(
        default=False,
        description="Yalnızca FAZ 3'te (%20 sınırı dahilinde) gelir linki/aksiyonu varsa true, aksi halde false.",
    )

    @model_validator(mode="after")
    def dogrula_anayasa_kurallari(self) -> "KanalKarari":
        for idx, tweet in enumerate(self.ana_tweetler, start=1):
            temiz = tweet.strip()
            if not temiz:
                raise ValueError(f"Tweet #{idx} boş olamaz.")
            if len(temiz) > 270:
                raise ValueError(
                    f"Tweet #{idx} 270 karakter sınırını aşıyor ({len(temiz)} karakter)."
                )
            if HASHTAG_REGEX.search(temiz):
                raise ValueError(f"Tweet #{idx} içinde hashtag yasaktır (0 hashtag kuralı).")
            if URL_REGEX.search(temiz):
                raise ValueError(
                    f"Tweet #{idx} içinde dış bağlantı (URL) yasaktır; link yalnızca ilk_yanit_metni içinde olabilir."
                )
            kucuk = temiz.lower()
            for klise in YASAKLI_KLISELER:
                if klise in kucuk:
                    raise ValueError(f"Tweet #{idx} yasaklı yapay zeka klişesi içeriyor: '{klise}'")
            if say_emoji(temiz) > 1:
                raise ValueError(f"Tweet #{idx} en fazla 1 emoji içerebilir.")

        if self.aksiyon_tipi == "flood" and not (5 <= len(self.ana_tweetler) <= 7):
            raise ValueError(
                f"Flood aksiyonu 5 ila 7 tweet içermelidir (mevcut: {len(self.ana_tweetler)})."
            )

        if self.aksiyon_tipi == "anket":
            if len(self.ana_tweetler) != 1:
                raise ValueError("Anket aksiyonunda ana_tweetler tek soru tweeti içermelidir.")
            if not (2 <= len(self.anket_secenekleri) <= 4):
                raise ValueError("Anket aksiyonu 2 ila 4 seçenek içermelidir.")
            for opt in self.anket_secenekleri:
                if len(opt.strip()) > 25:
                    raise ValueError(
                        f"X anket seçeneği en fazla 25 karakter olabilir: '{opt}' ({len(opt.strip())})"
                    )

        if self.aktif_faz in (1, 2) and self.gelir_aksiyonu_var_mi:
            raise ValueError("FAZ 1 ve FAZ 2'de gelir/satış aksiyonu kesinlikle yasaktır.")

        if self.aktif_faz in (1, 2) and self.ilk_yanit_metni:
            if URL_REGEX.search(self.ilk_yanit_metni):
                raise ValueError("FAZ 1 ve FAZ 2'de ilk yanıtta dahi satış/dış link paylaşılamaz.")

        return self
