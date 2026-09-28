#!/usr/bin/env python3
"""Генерує картинки циферблата для Amazfit Bip 6 (390x450) і вписує координати у watchface/index.js.

Запуск із кореня репозиторію:
    pip install pillow fonttools
    python3 tools/gen_assets.py

Шрифт Roboto Flex (SIL Open Font License) завантажується з github.com/google/fonts
у tools/fonts/ і в репозиторій не комітиться. У пакет потрапляють лише згенеровані PNG.
"""
import os
import re
import urllib.request

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image, ImageDraw, ImageFont

# ------------------------------------------------------------------ налаштування
COLOR = (255, 140, 0)          # помаранчевий #FF8C00
SCREEN_W, SCREEN_H, RADIUS = 390, 450, 86

TIME_AXES = {"wght": 500, "wdth": 55, "opsz": 144, "GRAD": 0, "slnt": 0}   # середня товщина, звужені цифри
TIME_SIZE = 236                 # px кегля -> висота цифр ~172 px
DATE_AXES = {"wght": 600, "wdth": 100, "opsz": 36, "GRAD": 0, "slnt": 0}
DATE_SIZE = 58                  # px кегля -> висота літер ~43 px
TRACKING = 2                    # міжлітерний інтервал для дати і дня тижня
DIGIT_PAD = 3                   # поля з боків кожної цифри часу
COLON_PAD = 5                   # поля з боків двокрапки
DATE_DIGIT_PAD = 2              # поля з боків цифр дати
GAP_TIME_DATE = 30              # відступ від часу до дати
GAP_DATE_WEEK = 16              # відступ від дати до дня тижня
GAP_DAY_MONTH = 18              # проміжок між числом і місяцем

MONTHS = ["СІЧ", "ЛЮТ", "БЕР", "КВІ", "ТРА", "ЧЕР", "ЛИП", "СЕР", "ВЕР", "ЖОВ", "ЛИС", "ГРУ"]
WEEKDAYS = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "НД"]  # у Zepp OS тиждень починається з понеділка

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets", "bip6")
FONT_DIR = os.path.join(ROOT, "tools", "fonts")
VF_NAME = "RobotoFlex[GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,opsz,slnt,wdth,wght].ttf"
VF_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/robotoflex/" + VF_NAME.replace("[", "%5B").replace("]", "%5D")


# ------------------------------------------------------------------ шрифти
def variable_font_path():
    os.makedirs(FONT_DIR, exist_ok=True)
    path = os.path.join(FONT_DIR, "RobotoFlex-VF.ttf")
    if not os.path.exists(path):
        urllib.request.urlretrieve(VF_URL, path)
    return path


def static_font(axes, size):
    tag = "_".join(f"{k}{v}" for k, v in sorted(axes.items()))
    path = os.path.join(FONT_DIR, f"RobotoFlex_{tag}.ttf")
    if not os.path.exists(path):
        inst = instancer.instantiateVariableFont(TTFont(variable_font_path()), axes, inplace=False)
        inst.save(path)
    return ImageFont.truetype(path, size)


# ------------------------------------------------------------------ рендер тексту
def draw_tracked(draw, x, y, text, font, tracking):
    for i, ch in enumerate(text):
        draw.text((x, y), ch, font=font, fill=255, anchor="ls")
        x += font.getlength(ch) + (tracking if i < len(text) - 1 else 0)


def ink_box(font, text, tracking=0):
    """Межі чорнила тексту відносно точки (0, базова лінія)."""
    img = Image.new("L", (3000, 900), 0)
    draw_tracked(ImageDraw.Draw(img), 800, 600, text, font, tracking)
    x0, y0, x1, y1 = img.getbbox()
    return x0 - 800, y0 - 600, x1 - 800, y1 - 600


def text_image(font, text, canvas_w, top, bottom, align, tracking=0):
    """PNG із прозорим фоном; усі картинки набору мають спільний вертикальний діапазон [top, bottom]."""
    box = ink_box(font, text, tracking)
    ink_w = box[2] - box[0]
    x = {"left": 0, "center": (canvas_w - ink_w) / 2, "right": canvas_w - ink_w}[align]
    mask = Image.new("L", (canvas_w, bottom - top), 0)
    draw_tracked(ImageDraw.Draw(mask), round(x - box[0]), -top, text, font, tracking)
    img = Image.new("RGBA", mask.size, COLOR + (0,))
    img.putalpha(mask)
    return img


def glyph_set(font, texts, align, pad=0, tracking=0):
    boxes = [ink_box(font, t, tracking) for t in texts]
    top = min(b[1] for b in boxes)
    bottom = max(b[3] for b in boxes)
    width = max(b[2] - b[0] for b in boxes) + 2 * pad
    return [text_image(font, t, width, top, bottom, align, tracking) for t in texts], width, bottom - top


def colon_image(font, height):
    """Двокрапка по центру висоти цифр."""
    box = ink_box(font, ":")
    w = box[2] - box[0] + 2 * COLON_PAD
    mask = Image.new("L", (w, height), 0)
    y = (height - (box[3] - box[1])) / 2 - box[1]
    ImageDraw.Draw(mask).text((COLON_PAD - box[0], round(y)), ":", font=font, fill=255, anchor="ls")
    img = Image.new("RGBA", mask.size, COLOR + (0,))
    img.putalpha(mask)
    return img


# ------------------------------------------------------------------ збірка
def main():
    time_font = static_font(TIME_AXES, TIME_SIZE)
    date_font = static_font(DATE_AXES, DATE_SIZE)

    digits, digit_w, time_h = glyph_set(time_font, [str(i) for i in range(10)], "center", DIGIT_PAD)
    colon = colon_image(time_font, time_h)
    colon_w = colon.width

    # дата і день тижня мають спільну висоту рядка, щоб усе стояло на одній базовій лінії
    date_texts = [str(i) for i in range(10)] + MONTHS + WEEKDAYS
    boxes = [ink_box(date_font, t, TRACKING) for t in date_texts]
    d_top, d_bottom = min(b[1] for b in boxes), max(b[3] for b in boxes)
    d_digit_w = max(ink_box(date_font, str(i))[2] - ink_box(date_font, str(i))[0] for i in range(10)) + 2 * DATE_DIGIT_PAD
    month_w = max(ink_box(date_font, m, TRACKING)[2] - ink_box(date_font, m, TRACKING)[0] for m in MONTHS)
    week_w = max(ink_box(date_font, w, TRACKING)[2] - ink_box(date_font, w, TRACKING)[0] for w in WEEKDAYS)
    date_digits = [text_image(date_font, str(i), d_digit_w, d_top, d_bottom, "center") for i in range(10)]
    months = [text_image(date_font, m, month_w, d_top, d_bottom, "left", TRACKING) for m in MONTHS]
    weeks = [text_image(date_font, w, week_w, d_top, d_bottom, "center", TRACKING) for w in WEEKDAYS]
    date_h = d_bottom - d_top

    # ---- координати (дизайн 390 px = екран Bip 6)
    time_w = 4 * digit_w + colon_w
    avg_month = sum(ink_box(date_font, m, TRACKING)[2] - ink_box(date_font, m, TRACKING)[0] for m in MONTHS) / 12
    date_group_w = 2 * d_digit_w + GAP_DAY_MONTH + avg_month
    block_h = time_h + GAP_TIME_DATE + date_h + GAP_DATE_WEEK + date_h
    y0 = round((SCREEN_H - block_h) / 2)
    L = {
        "TIME_Y": y0,
        "HOUR_X": round((SCREEN_W - time_w) / 2),
        "DATE_Y": y0 + time_h + GAP_TIME_DATE,
        "DAY_X": round((SCREEN_W - date_group_w) / 2),
        "WEEK_X": round((SCREEN_W - week_w) / 2),
        "WEEK_Y": y0 + time_h + GAP_TIME_DATE + date_h + GAP_DATE_WEEK,
    }
    L["COLON_X"] = L["HOUR_X"] + 2 * digit_w
    L["MINUTE_X"] = L["COLON_X"] + colon_w
    L["MONTH_X"] = L["DAY_X"] + 2 * d_digit_w + GAP_DAY_MONTH
    L["DIGIT_W"], L["DATE_DIGIT_W"] = digit_w, d_digit_w

    # ---- запис картинок
    for sub in ("time", "date", "month", "week"):
        os.makedirs(os.path.join(ASSETS, sub), exist_ok=True)
    for i, im in enumerate(digits):
        im.save(os.path.join(ASSETS, "time", f"{i}.png"))
    colon.save(os.path.join(ASSETS, "time", "colon.png"))
    for i, im in enumerate(date_digits):
        im.save(os.path.join(ASSETS, "date", f"{i}.png"))
    for i, im in enumerate(months, start=1):
        im.save(os.path.join(ASSETS, "month", f"{i}.png"))
    for i, im in enumerate(weeks, start=1):
        im.save(os.path.join(ASSETS, "week", f"{i}.png"))

    # ---- макет екрана (так само, як малюватиме годинник) і прев'ю для Zepp
    def screen(hh, mm, day, month, weekday):
        s = Image.new("RGBA", (SCREEN_W, SCREEN_H), (0, 0, 0, 255))
        x = L["HOUR_X"]
        for ch in f"{hh:02d}":
            s.alpha_composite(digits[int(ch)], (x, L["TIME_Y"]))
            x += digit_w
        s.alpha_composite(colon, (L["COLON_X"], L["TIME_Y"]))
        x = L["MINUTE_X"]
        for ch in f"{mm:02d}":
            s.alpha_composite(digits[int(ch)], (x, L["TIME_Y"]))
            x += digit_w
        x = L["DAY_X"]
        for ch in f"{day:02d}":
            s.alpha_composite(date_digits[int(ch)], (x, L["DATE_Y"]))
            x += d_digit_w
        s.alpha_composite(months[month - 1], (L["MONTH_X"], L["DATE_Y"]))
        s.alpha_composite(weeks[weekday - 1], (L["WEEK_X"], L["WEEK_Y"]))
        return s

    def rounded(img, radius):
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=radius, fill=255)
        out = img.copy()
        out.putalpha(mask)
        return out

    sample = screen(12, 27, 28, 9, 1)
    preview = rounded(sample.resize((266, 307), Image.LANCZOS), round(RADIUS * 266 / 390))
    preview.save(os.path.join(ASSETS, "preview.png"))
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    rounded(sample, RADIUS).save(os.path.join(ROOT, "docs", "preview.png"))

    raw = sample.convert("RGB").tobytes()
    lit = sum(max(raw[i:i + 3]) for i in range(0, len(raw), 3)) / 255 / (SCREEN_W * SCREEN_H)

    # ---- координати у watchface/index.js
    js_path = os.path.join(ROOT, "watchface", "index.js")
    block = "\n".join(f"const {k} = {v}" for k, v in sorted(L.items()))
    with open(js_path, encoding="utf-8") as f:
        src = f.read()
    src = re.sub(r"(// <layout>\n).*?(// </layout>)", lambda m: m.group(1) + block + "\n" + m.group(2), src, flags=re.S)
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(src)

    print("layout:", L)
    print(f"time {time_w}x{time_h}px, date line {date_h}px, lit pixels {lit:.1%}")


if __name__ == "__main__":
    main()
