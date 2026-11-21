"""@turkprincee Otonom Görsel & Animasyon Stüdyosu (0 TL — Hareketli Telemetri GIF ve İnfografik Üretici)."""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

BG_DARK = (11, 14, 20)
CARD_BG = (19, 25, 36)
BORDER = (34, 46, 66)
CYAN = (0, 229, 255)
AMBER = (255, 107, 0)
RED = (255, 69, 96)
GREEN = (16, 185, 129)
TEXT_MAIN = (232, 238, 247)
TEXT_MUTED = (139, 149, 167)


def _yukle_font(boyut: int, kalin: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    adaylar = (
        [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        if kalin
        else [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    )
    for yol in adaylar:
        if Path(yol).exists():
            try:
                return ImageFont.truetype(yol, boyut)
            except Exception:
                continue
    return ImageFont.load_default()


def _ciz_ust_alt_antet(
    draw: ImageDraw.ImageDraw,
    w: int,
    h: int,
    ust_etiket: str,
    baslik: str,
    alt_not: str,
) -> None:
    f_tag = _yukle_font(16, kalin=True)
    f_title = _yukle_font(28, kalin=True)
    f_foot = _yukle_font(16, kalin=False)

    # Üst ince ızgara çizgisi ve dinamik genişlikli rozet
    etiket_w = int(draw.textlength(ust_etiket, font=f_tag)) + 28
    draw.rectangle((0, 0, w, 5), fill=CYAN)
    draw.rounded_rectangle((36, 24, 36 + etiket_w, 54), radius=6, fill=(14, 36, 48), outline=CYAN, width=1)
    draw.text((48, 29), ust_etiket, font=f_tag, fill=CYAN)
    draw.text((36, 66), baslik, font=f_title, fill=TEXT_MAIN)

    # Alt marka bandı
    draw.line((36, h - 52, w - 36, h - 52), fill=BORDER, width=1)
    draw.text((36, h - 38), alt_not, font=f_foot, fill=TEXT_MUTED)
    draw.text((w - 295, h - 38), "Donanım & Oyun Lab · @turkprincee", font=f_tag, fill=CYAN)


def _kaydet_gif(kareler: List[Image.Image], cikti_yolu: Path, sure_ms: int = 55) -> Path:
    cikti_yolu.parent.mkdir(parents=True, exist_ok=True)
    paletli = [k.quantize(colors=128, method=Image.Quantize.MEDIANCUT) for k in kareler]
    paletli[0].save(
        cikti_yolu,
        save_all=True,
        append_images=paletli[1:],
        duration=sure_ms,
        loop=0,
        optimize=True,
    )
    return cikti_yolu


def uret_ghosting_karsilastirma_gif(cikti_yolu: Path) -> Path:
    """1ms MPRT vs Ucuz VA Ghosting vs 0.03ms OLED GtG canlı hareket simülasyonu GIF."""
    w, h = 960, 540
    kare_sayisi = 28
    kareler: List[Image.Image] = []
    f_sub = _yukle_font(20, kalin=True)
    f_val = _yukle_font(17, kalin=False)

    seritler = [
        ("UCUZ VA PANEL ('Kutuda 1 ms MPRT')", "Gerçek GtG: ~11.4 ms · Koyu Siyah Gölgelenme (Smearing)", RED, 132),
        ("ORTA SEGMENT IPS ('1 ms MPRT Strobe')", "Gerçek GtG: ~5.2 ms · Hafif Çift Görüntü İzi", AMBER, 258),
        ("QD-OLED / WOLED PANEL (Gerçek 0.03 ms GtG)", "Anlık Piksel Geçişi · Sıfır Ghosting / Cam Gibi Net", CYAN, 384),
    ]

    for i in range(kare_sayisi):
        im = Image.new("RGB", (w, h), BG_DARK)
        draw = ImageDraw.Draw(im)
        _ciz_ust_alt_antet(
            draw,
            w,
            h,
            "CANLI HAREKET TESTİ · MPRT vs GtG",
            "Kutudaki '1 ms MPRT' Neden Gerçek Hız Değildir?",
            "Hareket eden hedefte gerçek piksel tepki süresi (GtG) farkı",
        )

        ilerleme = i / kare_sayisi
        x_pos = int(90 + ilerleme * (w - 220))

        for ad, aciklama, renk, y_top in seritler:
            draw.rounded_rectangle((36, y_top, w - 36, y_top + 106), radius=12, fill=CARD_BG, outline=BORDER, width=1)
            draw.text((54, y_top + 10), ad, font=f_sub, fill=renk)
            draw.text((54, y_top + 36), aciklama, font=f_val, fill=TEXT_MUTED)

            cy = y_top + 78
            draw.line((56, cy, w - 56, cy), fill=(28, 36, 52), width=2)

            if renk == RED:
                # Koyu smearing kuyruğu
                for iz in range(6, 0, -1):
                    gx = x_pos - iz * 15
                    if gx > 54:
                        oran = (7 - iz) / 8.0
                        kuyruk_renk = (
                            int(18 + (renk[0] - 18) * oran * 0.55),
                            int(24 + (renk[1] - 24) * oran * 0.35),
                            int(36 + (renk[2] - 36) * oran * 0.35),
                        )
                        draw.rounded_rectangle((gx - 18, cy - 14, gx + 18, cy + 14), radius=6, fill=kuyruk_renk)
            elif renk == AMBER:
                # Strobe çift görüntü (double image)
                gx = x_pos - 26
                if gx > 54:
                    draw.rounded_rectangle((gx - 18, cy - 14, gx + 18, cy + 14), radius=6, outline=(130, 75, 25), width=2)

            # Ana hareketli hedef kutusu + nişangâh
            draw.rounded_rectangle((x_pos - 18, cy - 14, x_pos + 18, cy + 14), radius=6, fill=renk)
            draw.line((x_pos, cy - 10, x_pos, cy + 10), fill=BG_DARK, width=2)
            draw.line((x_pos - 10, cy, x_pos + 10, cy), fill=BG_DARK, width=2)

        kareler.append(im)

    return _kaydet_gif(kareler, cikti_yolu, sure_ms=55)


def uret_vram_pcie_darbogaz_gif(cikti_yolu: Path) -> Path:
    """8 GB VRAM PCIe taşması (%1 Low FPS çöküşü) vs 16 GB VRAM stabil frametime animasyonu."""
    w, h = 960, 540
    kare_sayisi = 28
    kareler: List[Image.Image] = []
    f_sub = _yukle_font(20, kalin=True)
    f_val = _yukle_font(18, kalin=True)
    f_small = _yukle_font(16, kalin=False)

    for i in range(kare_sayisi):
        im = Image.new("RGB", (w, h), BG_DARK)
        draw = ImageDraw.Draw(im)
        _ciz_ust_alt_antet(
            draw,
            w,
            h,
            "CANLI TELEMETRİ · FRAMETIME & %1 LOW FPS",
            "8 GB VRAM Dolduğunda Oyun Neden Takılır (Stutter)?",
            "Ortalama FPS yakın görünse bile PCIe RAM taşması %1 Low FPS'i çökertir",
        )

        # Üst Kart: 8 GB VRAM (Stutter spikes)
        draw.rounded_rectangle((36, 128, w - 36, 292), radius=12, fill=CARD_BG, outline=BORDER)
        draw.text((54, 140), "8 GB VRAM (Yüksek Doku + Frame Gen -> PCIe Taşması)", font=f_sub, fill=RED)
        draw.text((w - 305, 142), "Ort: 84 FPS | %1 Low: 29 FPS", font=f_val, fill=RED)

        # Alt Kart: 16 GB VRAM (Düz çizgi)
        draw.rounded_rectangle((36, 310, w - 36, 474), radius=12, fill=CARD_BG, outline=BORDER)
        draw.text((54, 322), "16 GB VRAM (Dokular GPU Belleğinde -> Sıfır Taşma)", font=f_sub, fill=CYAN)
        draw.text((w - 305, 324), "Ort: 91 FPS | %1 Low: 78 FPS", font=f_val, fill=GREEN)

        # Osiloskop frametime çizgileri
        pts_8gb: List[Tuple[int, int]] = []
        pts_16gb: List[Tuple[int, int]] = []
        for s in range(44):
            px = 58 + s * 19
            idx = (s + i) % 14
            spike = 68 if idx in (4, 11) else (28 if idx == 5 else int(6 * math.sin((s + i) * 0.7)))
            py_8 = 252 - max(0, spike)
            pts_8gb.append((px, py_8))

            dalga_16 = int(4 * math.sin((s + i) * 0.5))
            py_16 = 432 - dalga_16
            pts_16gb.append((px, py_16))

        draw.line(pts_8gb, fill=RED, width=3)
        draw.line(pts_16gb, fill=CYAN, width=3)
        draw.text((58, 266), "Frametime Sıçramaları: 11.9 ms -> 46.5 ms (Anlık Donma!)", font=f_small, fill=TEXT_MUTED)
        draw.text((58, 446), "Sabit Frametime: 10.9 ms - 12.1 ms (Akıcı Çizgi)", font=f_small, fill=TEXT_MUTED)

        kareler.append(im)

    return _kaydet_gif(kareler, cikti_yolu, sure_ms=65)


def uret_wifi_kanal_ping_gif(cikti_yolu: Path) -> Path:
    """2.4 GHz Kalabalık Kanal / Repeater vs 5 GHz Doğru Kanal / Kablolu AP Jitter Animasyonu."""
    w, h = 960, 540
    kare_sayisi = 26
    kareler: List[Image.Image] = []
    f_sub = _yukle_font(20, kalin=True)
    f_big = _yukle_font(34, kalin=True)
    f_small = _yukle_font(16, kalin=False)

    for i in range(kare_sayisi):
        im = Image.new("RGB", (w, h), BG_DARK)
        draw = ImageDraw.Draw(im)
        _ciz_ust_alt_antet(
            draw,
            w,
            h,
            "AĞ LABORATUVARI · PING & PACKET JITTER",
            "İndirme Hızınız 500 Mbps İken Oyunda Neden Lag Olur?",
            "Oyunlarda hız (Mbps) değil, paket gecikme sapması (Jitter ms) belirleyicidir",
        )

        # Sol Kutu: Priz Tipi Repeater / Otomatik 2.4GHz
        draw.rounded_rectangle((36, 130, 466, 468), radius=12, fill=CARD_BG, outline=BORDER)
        draw.text((56, 148), "Priz Tipi Repeater / 2.4 GHz", font=f_sub, fill=RED)
        draw.text((56, 178), "Yarı-Dupleks Tek Radyo · Komşu Paraziti", font=f_small, fill=TEXT_MUTED)
        jitter_ping = 24 + int(abs(math.sin(i * 0.55)) * 95) + (42 if i % 7 == 0 else 0)
        draw.text((56, 224), f"Ping: {jitter_ping} ms", font=f_big, fill=RED if jitter_ping > 65 else AMBER)

        bar_w = min(380, int(jitter_ping * 2.4))
        draw.rounded_rectangle((56, 286, 440, 316), radius=6, fill=(28, 35, 48))
        draw.rounded_rectangle((56, 286, 56 + bar_w, 316), radius=6, fill=RED)
        draw.text((56, 340), "• Hızı %50 keser, gecikmeyi 2x katlar", font=f_small, fill=TEXT_MAIN)
        draw.text((56, 370), "• Anlık 110+ ms Jitter = Mermi gitmeme hissi", font=f_small, fill=TEXT_MAIN)
        draw.text((56, 400), "• Mikrodalga ve Bluetooth ile aynı 2.4 GHz bant", font=f_small, fill=TEXT_MUTED)

        # Sağ Kutu: 5 GHz Sabit Kanal (36/44) veya Kablolu AP
        draw.rounded_rectangle((494, 130, w - 36, 468), radius=12, fill=CARD_BG, outline=CYAN)
        draw.text((514, 148), "5 GHz Sabit Kanal (36-48) / AP", font=f_sub, fill=CYAN)
        draw.text((514, 178), "80 MHz Temiz Kanal · Tam Dupleks Akış", font=f_small, fill=TEXT_MUTED)
        sabit_ping = 14 + (i % 2)
        draw.text((514, 224), f"Ping: {sabit_ping} ms", font=f_big, fill=GREEN)

        bar_w2 = int(sabit_ping * 2.4)
        draw.rounded_rectangle((514, 286, w - 56, 316), radius=6, fill=(28, 35, 48))
        draw.rounded_rectangle((514, 286, 514 + bar_w2, 316), radius=6, fill=GREEN)
        draw.text((514, 340), "• Jitter < 1.5 ms (Turnuva standardı stabilite)", font=f_small, fill=TEXT_MAIN)
        draw.text((514, 370), "• Modem arayüzünde 5 GHz Kanal: 36 veya 44 seçin", font=f_small, fill=TEXT_MAIN)
        draw.text((514, 400), "• DFS radar kopması yaşamadan tam performans", font=f_small, fill=TEXT_MUTED)

        kareler.append(im)

    return _kaydet_gif(kareler, cikti_yolu, sure_ms=70)


def uret_dinamik_karsilastirma_karti(
    cikti_yolu: Path,
    ust_etiket: str,
    baslik: str,
    sol_baslik: str,
    sol_maddeler: List[str],
    sag_baslik: str,
    sag_maddeler: List[str],
    alt_not: str = "Gerçek donanım ve oyun telemetri analizi",
) -> Path:
    """Bulut motorunun her dilimde dinamik üretebildiği 16:9 animasyonlu nabız GIF kartı."""
    w, h = 960, 540
    kareler: List[Image.Image] = []
    f_sub = _yukle_font(21, kalin=True)
    f_item = _yukle_font(17, kalin=False)

    for i in range(16):
        im = Image.new("RGB", (w, h), BG_DARK)
        draw = ImageDraw.Draw(im)
        _ciz_ust_alt_antet(draw, w, h, ust_etiket, baslik[:54], alt_not[:75])

        parlak = int(170 + 85 * math.sin(i * 2 * math.pi / 16))
        sag_cerceve = (0, int(parlak * 0.9), parlak)

        draw.rounded_rectangle((36, 130, 466, 468), radius=12, fill=CARD_BG, outline=RED, width=2)
        draw.text((56, 148), sol_baslik[:32], font=f_sub, fill=RED)
        for idx, m in enumerate(sol_maddeler[:4]):
            draw.text((56, 198 + idx * 58), f"✕  {m[:42]}", font=f_item, fill=TEXT_MAIN)

        draw.rounded_rectangle((494, 130, w - 36, 468), radius=12, fill=CARD_BG, outline=sag_cerceve, width=2)
        draw.text((514, 148), sag_baslik[:32], font=f_sub, fill=CYAN)
        for idx, m in enumerate(sag_maddeler[:4]):
            draw.text((514, 198 + idx * 58), f"✓  {m[:42]}", font=f_item, fill=TEXT_MAIN)

        kareler.append(im)

    return _kaydet_gif(kareler, cikti_yolu, sure_ms=75)
