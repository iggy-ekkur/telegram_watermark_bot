from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import io
import os

def _load_font(font_size: int) -> ImageFont.FreeTypeFont:
    # 1) пытаемся взять шрифт из проекта: ./fonts/arialbd.ttf
    try:
        base_dir = Path(__file__).resolve().parent
    except NameError:
        # если запускаешь интерактивно (где нет __file__), берём текущую директорию
        base_dir = Path(os.getcwd())

    candidates = [
        base_dir / "fonts" / "arialbd.ttf",                         # твой бандл
        "/Library/Fonts/Arial Bold.ttf",                            # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",        # macOS доп путь
        "C:/Windows/Fonts/arialbd.ttf",                             # Windows
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",     # Linux
    ]

    for p in candidates:
        p = Path(p)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), font_size)
            except Exception:
                pass

    # крайний вариант — дефолт (может иначе мерить метрики)
    return ImageFont.load_default()

def add_watermark(image_bytes: bytes, text: str = "FLP STONE") -> io.BytesIO:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    font_size = max(20, int(min(image.size) / 9))
    font = _load_font(font_size)

    # слой для водяного знака
    temp = Image.new("RGBA", image.size, (255, 255, 255, 0))
    d = ImageDraw.Draw(temp)

    # метрики текста — работаем и на старых, и на новых версиях Pillow
    try:
        bbox = font.getbbox(text)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        bbox = d.textbbox((0, 0), text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    cx = (image.width - text_w) / 2
    cy = (image.height - text_h) / 2

    # тень + основной текст
    d.text((cx + 2, cy + 2), text, font=font, fill=(0, 0, 0, 100))
    d.text((cx, cy), text, font=font, fill=(255, 255, 255, 130))

    # поворот
    rotated = temp.rotate(-30, resample=Image.BICUBIC)
    combined = Image.alpha_composite(image, rotated)

    # JPEG без альфы
    out = io.BytesIO()
    combined.convert("RGB").save(out, format="JPEG", quality=95, optimize=True)
    out.seek(0)
    return out
