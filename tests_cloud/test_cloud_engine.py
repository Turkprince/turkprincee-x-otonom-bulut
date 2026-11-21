"""@turkprincee Bulut Otonom Kanal Motoru — Birim Testleri."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from cloud.run_slot import (
    TSI,
    belirle_aktif_dilim,
    bu_dilim_zaten_yayinlandi_mi,
    temizle_eski_hafiza,
    yaz_durum_paneli,
    yukle_hafiza,
)
from cloud.schemas import KanalKarari, hesapla_aktif_faz


class CloudEngineTestleri(unittest.TestCase):
    def test_faz_gecis_kurallari(self) -> None:
        self.assertEqual(hesapla_aktif_faz(0), 1)
        self.assertEqual(hesapla_aktif_faz(21), 1)
        self.assertEqual(hesapla_aktif_faz(2999), 1)
        self.assertEqual(hesapla_aktif_faz(3000), 2)
        self.assertEqual(hesapla_aktif_faz(9999), 2)
        self.assertEqual(hesapla_aktif_faz(10000), 3)

    def test_gecerli_tek_tweet_karari(self) -> None:
        karar = KanalKarari(
            aktif_faz=1,
            aksiyon_tipi="tek_tweet",
            bekleme_dakika=7,
            hedef_tweet_id=None,
            ana_tweetler=[
                "GTA 6 oynarken 120Hz TV'de VRR kapalıysa konsol 30 FPS kilidine düşer ve frametime 33.3 ms olur.\n\nHDMI 2.1 portunda VRR + 120Hz açtığınızda 40 FPS denge modu devreye girer; giriş gecikmesi 8.3 ms iyileşir."
            ],
            anket_secenekleri=[],
            ilk_yanit_metni=None,
            gorsel_prompt_en=None,
            hafiza_ozeti="GTA 6 120Hz VRR ve 40 FPS 25ms frametime ayarı",
            gelir_aksiyonu_var_mi=False,
        )
        self.assertEqual(karar.aktif_faz, 1)

    def test_270_karakter_asimini_reddeder(self) -> None:
        with self.assertRaises(ValueError):
            KanalKarari(
                aktif_faz=1,
                aksiyon_tipi="tek_tweet",
                bekleme_dakika=5,
                ana_tweetler=["A" * 271],
                hafiza_ozeti="Uzun tweet testi 271 karakter",
            )

    def test_hashtag_url_ve_kliseyi_reddeder(self) -> None:
        for hatali in (
            "OLED panellerde GtG 0.03 ms seviyesindedir #donanim",
            "Detaylı test tablosu https://example.com adresinde",
            "Merhaba arkadaşlar bugün VRAM darboğazını konuşuyoruz.",
        ):
            with self.assertRaises(ValueError):
                KanalKarari(
                    aktif_faz=1,
                    aksiyon_tipi="tek_tweet",
                    bekleme_dakika=6,
                    ana_tweetler=[hatali],
                    hafiza_ozeti="Yasaklı kural testi kontrolü",
                )

    def test_faz1_satis_linkini_reddeder(self) -> None:
        with self.assertRaises(ValueError):
            KanalKarari(
                aktif_faz=1,
                aksiyon_tipi="tek_tweet",
                bekleme_dakika=8,
                ana_tweetler=["2x16 GB DDR5 çift kanal kurulum %1 Low FPS değerini %15 artırır."],
                ilk_yanit_metni="İndirimli ürün linki: https://ornek-magaza.com/ram",
                hafiza_ozeti="DDR5 çift kanal testi",
                gelir_aksiyonu_var_mi=False,
            )

    def test_anket_secenek_siniri(self) -> None:
        karar = KanalKarari(
            aktif_faz=1,
            aksiyon_tipi="anket",
            bekleme_dakika=9,
            ana_tweetler=["Aynı bütçede oyun için hangi monitör panelini seçersiniz?"],
            anket_secenekleri=["27 inç 1440p QD-OLED", "27 inç 4K Mini-LED IPS"],
            hafiza_ozeti="QD-OLED vs Mini-LED IPS oyuncu monitörü anketi",
        )
        self.assertEqual(len(karar.anket_secenekleri), 2)

    def test_dilim_secimi_ve_cift_yayin_korumasi(self) -> None:
        dt = datetime(2026, 11, 21, 9, 32, tzinfo=TSI)
        self.assertEqual(belirle_aktif_dilim(dt), "09:30")
        hafiza = {
            "son_14_gun_konu_hafizasi": [
                {"tarih_tsi": "2026-11-21T09:38:00+03:00", "dilim": "09:30"}
            ]
        }
        self.assertTrue(bu_dilim_zaten_yayinlandi_mi(hafiza, "2026-11-21", "09:30"))
        self.assertFalse(bu_dilim_zaten_yayinlandi_mi(hafiza, "2026-11-21", "13:00"))

    def test_14_gun_hafiza_temizligi_ve_durum_paneli(self) -> None:
        simdi = datetime(2026, 11, 21, 12, 0, tzinfo=TSI)
        kayitlar = [
            {"tarih_tsi": (simdi - timedelta(days=16)).isoformat(), "konu_ozeti": "eski"},
            {"tarih_tsi": (simdi - timedelta(days=2)).isoformat(), "konu_ozeti": "yeni"},
        ]
        temiz = temizle_eski_hafiza(kayitlar, simdi)
        self.assertEqual(len(temiz), 1)
        self.assertEqual(temiz[0]["konu_ozeti"], "yeni")

        hafiza = yukle_hafiza()
        yaz_durum_paneli(hafiza, "Test Başarılı")


if __name__ == "__main__":
    unittest.main()
