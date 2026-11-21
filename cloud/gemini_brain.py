"""Gemini 3.8 Flash + Google Search Grounding + Yapılandırılmış JSON Karar Motoru."""

from __future__ import annotations

import json
import os
import secrets
from typing import Any, Dict, List, Optional
from google import genai
from pydantic import ValidationError

from .schemas import KanalKarari, hesapla_aktif_faz

SISTEM_TALIMATI = """Sen, insan müdahalesi olmadan 7/24 karar alıp uygulayan tam otonom bir X (Twitter) Kanal Yöneticisi, Teknoloji/Donanım/Oyun Editörü ve Gelir Stratejistisin.
Hesap: @turkprincee (Donanım & Oyun Lab).
Odak: Teknoloji, PC/konsol donanımı, monitör/TV panelleri, ağ/ev ekipmanları, tüketici elektroniği ve oyun dünyası.

KESİN ANAYASA KURALLARI:
1. Yapay zekâ klişeleri ("Merhaba arkadaşlar", "Harika bir haber", "Gelin birlikte inceleyelim", "İşte detaylar", "Sizler için derledik", "Hazırsanız başlayalım") KESİNLİKLE YASAKTIR.
2. İlk 2 satırda akışı durduran çarpıcı bir veri, yaygın bir yanılgıyı yıkan gerçek veya güçlü bir zıtlıkla başla.
3. Boş sıfatlar yerine gerçek teknik metrikler kullan (Hz, nit, GtG vs MPRT, OLED yanma koruması, VRAM, %1 Low FPS, frametime ms, VRR, PCIe veri yolu, Wi-Fi bant genişliği, yarı-dupleks latency, pil şarj döngüsü, 12V ripple vb.) ama herkesin anlayacağı netlikte anlat.
4. Her bir tweet KESİNLİKLE en fazla 265 karakter olsun (270 karakter tavanını asla aşma). Kısa cümleler ve mobilde 3 saniyede taranacak satır boşlukları kullan.
5. 0 hashtag (# işareti kesinlikle kullanma). Emoji en fazla 1 adet veya tercihen 0 olsun.
6. Ana tweetlerin içine ASLA dış bağlantı (URL) koyma.
7. Son 14 gün konu hafızasındaki hiçbir konuyu veya benzer açıyı tekrar etme.
8. FAZ KURALLARI:
   - FAZ 1 (0-2999 takipçi): Sıfır satış linki/reklam. gelir_aksiyonu_var_mi=false, ilk_yanit_metni içinde link yok.
   - FAZ 2 (3000-9999 takipçi): Dwell time yüksek derin teknik flood ve tartışmalar. Satış linki yok; gelir_aksiyonu_var_mi=false.
   - FAZ 3 (10000+ takipçi): Toplam içeriklerin en fazla %20'sinde önce yüksek teknik değer ver, satış/affiliate/abonelik bilgisini YALNIZCA ilk_yanit_metni alanına doğal tavsiye diliyle koy.
9. Flood aksiyonlarında her tweeti "1/ ...", "2/ ..." şeklinde numaralandır ve toplam 5 ila 7 tweet üret.
10. Anket aksiyonlarında ana_tweetler 1 adet tartışma sorusu içersin, anket_secenekleri ise her biri en fazla 25 karakter olan 2 ila 4 net seçenekten oluşsun.
"""

DILIM_GOREVLERI = {
    "09:30": (
        "SABAH TESPİT / GÜNDEM (09:30): Son 24 saatin en dikkat çekici teknoloji, donanım veya oyun "
        "gelişmesine tek tweetlik (aksiyon_tipi='tek_tweet') keskin, özgün ve paylaşılabilir analiz üret. "
        "Eğer açık döngü kuyruğunda bu sabah için söz verilmiş bir konu varsa ÖNCELİKLE o sözü yerine getir."
    ),
    "13:00": (
        "ÖĞLE TARTIŞMA / ANKET (13:00): İki popüler donanım, konsol, panel veya oyun yaklaşımını çarpıştıran "
        "2-4 seçenekli anket (aksiyon_tipi='anket', her seçenek <=25 karakter) üret."
    ),
    "16:30": (
        "ETKİLEŞİM VE TRAFİK DALGASI (16:30): Eğer hedef aday tweet listesinde uygun bir tweet ID varsa "
        "aksiyon_tipi='alinti' ile hedef_tweet_id belirterek teknik derinlik katan keskin bir alıntı üret; "
        "aday tweet ID yoksa aksiyon_tipi='tek_tweet' ile bugün ana akım teknoloji/oyun medyasının gözden kaçırdığı "
        "kritik bir teknik detayı ortaya koyan yüksek etkileşimli karşıt görüş analizi üret."
    ),
    "20:30": (
        "AKŞAM ANA FLOOD - PRIME TIME (20:30): Günün ana içeriği. aksiyon_tipi='flood' seçerek 5 ila 7 tweetten "
        "oluşan, '1/', '2/'... şeklinde numaralandırılmış, yoğun teknik değer taşıyan, yer imine kaydettiren "
        "rehber, satın alma tuzağı veya donanım/oyun analizi üret."
    ),
    "23:15": (
        "GECE MİKRO İPUCU VE MERAK KANCASI (23:15): aksiyon_tipi='tek_tweet' seçerek gece aktif kullanıcıların "
        "hemen uygulayabileceği tek ekranlık gizli cihaz/Windows/konsol/ağ/oyun ayarı ver ve son cümlede "
        "yarın sabah 09:30'da paylaşacağın spesifik bir teknik analize merak bırakan açık döngü (open loop) kur."
    ),
}


def _faz3_gelir_izni_var_mi(hafiza: Dict[str, Any], aktif_faz: int) -> bool:
    if aktif_faz < 3:
        return False
    son_kayitlar = hafiza.get("son_14_gun_konu_hafizasi", [])[-5:]
    gelir_sayisi = sum(1 for k in son_kayitlar if k.get("gelir_aksiyonu_var_mi"))
    return gelir_sayisi == 0


def uret_kanal_karari(
    dilim: str,
    hafiza: Dict[str, Any],
    rss_basliklari: List[Dict[str, str]],
    aday_hedef_tweetler: Optional[List[Dict[str, str]]] = None,
    zorunlu_bekleme_dakika: Optional[int] = None,
) -> KanalKarari:
    """Gemini Interactions API üzerinden geçerli ve doğrulanmış KanalKarari üretir."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY ortam değişkeni tanımlı değil.")

    model_tercih = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash"
    ucretsiz_modeller = []
    for m in (model_tercih, "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"):
        if m not in ucretsiz_modeller:
            ucretsiz_modeller.append(m)
    client = genai.Client(api_key=api_key)

    takipci = int(hafiza.get("kanal", {}).get("son_takipci_sayisi", 21))
    aktif_faz = hesapla_aktif_faz(takipci)
    bekleme = (
        zorunlu_bekleme_dakika
        if zorunlu_bekleme_dakika is not None
        else secrets.randbelow(12) + 3
    )

    son_14_gun = [
        {"tarih": k.get("tarih_tsi"), "dilim": k.get("dilim"), "konu": k.get("konu_ozeti")}
        for k in hafiza.get("son_14_gun_konu_hafizasi", [])[-40:]
    ]
    acik_donguler = [
        d for d in hafiza.get("acik_dongu_kuyrugu", []) if not d.get("tamamlandi", False)
    ]
    gelir_izni = _faz3_gelir_izni_var_mi(hafiza, aktif_faz)

    istem = json.dumps(
        {
            "aktif_zaman_dilimi_tsi": dilim,
            "dilim_gorevi": DILIM_GOREVLERI.get(dilim, DILIM_GOREVLERI["09:30"]),
            "guncel_takipci_sayisi": takipci,
            "hesaplanan_aktif_faz": aktif_faz,
            "atanacak_bekleme_dakika": bekleme,
            "faz3_gelir_aksiyonu_kullanilabilir_mi": gelir_izni,
            "bekleyen_acik_dongu_sozleri": acik_donguler,
            "son_14_gun_islenen_konular_TEKRAR_ETME": son_14_gun,
            "canli_rss_gundem_basliklari": rss_basliklari[:20],
            "aday_hedef_tweetler_1630_icin": aday_hedef_tweetler or [],
        },
        ensure_ascii=False,
        indent=2,
    )

    son_hata = None
    ek_uyari = ""
    model_idx = 0
    for deneme in range(4):
        secili_model = ucretsiz_modeller[min(model_idx, len(ucretsiz_modeller) - 1)]
        tam_girdi = istem if not ek_uyari else f"{istem}\n\nÖNCEKİ DENEME HATASI (DÜZELT): {ek_uyari}"
        try:
            interaction = client.interactions.create(
                model=secili_model,
                system_instruction=SISTEM_TALIMATI,
                input=tam_girdi,
                tools=[{"type": "google_search"}, {"type": "url_context"}],
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": KanalKarari.model_json_schema(),
                },
            )
        except Exception as api_exc:
            son_hata = str(api_exc)
            model_idx += 1
            continue
        ham_json = (interaction.output_text or "").strip()
        try:
            karar = KanalKarari.model_validate_json(ham_json)
            karar.aktif_faz = aktif_faz
            karar.bekleme_dakika = bekleme
            if not gelir_izni:
                karar.gelir_aksiyonu_var_mi = False
            return karar
        except ValidationError as exc:
            son_hata = str(exc)
            ek_uyari = (
                f"Şema/Anayasa doğrulama hatası oluştu: {son_hata}. "
                "Lütfen karakter sınırını (<=265), 0 hashtag, 0 URL, 0 klişe ve seçenek boyutu (<=25) kurallarını kesin sağlayarak yeniden üret."
            )

    raise RuntimeError(f"3 deneme sonunda geçerli karar üretilemedi: {son_hata}")
