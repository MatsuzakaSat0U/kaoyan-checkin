# -*- coding: utf-8 -*-
"""用 Pillow 直接画计划卡，不再依赖 Chrome 截图。

本地（Windows）和云端（Ubuntu runner）共用这一份：
- 路径都相对脚本，不写死 D:\考研
- 字体按候选列表探测，云端靠 apt 装 Noto CJK
"""
import json
import os
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
DATA = HERE / "plan_days.json"
if not DATA.exists():                      # 本地跑时计划表在上一级 _push/
    DATA = HERE.parent / "plan_days.json"
WORK = HERE / "_tmp" / "card"
PNG = WORK / "card.png"

SCALE = 2                      # 1800px 宽
W = 900


def _font_path(*cands):
    for c in cands:
        if c and Path(c).exists():
            return c
    raise SystemExit("找不到中文字体，用 PLAN_FONT_REG / PLAN_FONT_BOLD 指定")


REG = _font_path(os.environ.get("PLAN_FONT_REG"),
                 r"C:\Windows\Fonts\msyh.ttc",
                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                 "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
BOLD = _font_path(os.environ.get("PLAN_FONT_BOLD"),
                  r"C:\Windows\Fonts\msyhbd.ttc",
                  "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
                  REG)

INK = (28, 28, 30)
GREY = (142, 142, 147)
GREY2 = (58, 58, 60)
RED = (192, 57, 43)
LINE = (229, 229, 234)
LINE2 = (236, 236, 241)


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else REG, size * SCALE)


def wrap(draw, text, f, maxw):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        if draw.textlength(cur + ch, font=f) > maxw and cur:
            lines.append(cur); cur = ""
        cur += ch
    if cur:
        lines.append(cur)
    return lines or [""]


def build(today=None, out=None):
    days = json.loads(DATA.read_text(encoding="utf-8"))
    today = today or date.today().isoformat()
    day = next((d for d in days if d["d"] == today), None)
    if not day:
        return None
    idx = [d["d"] for d in days].index(today) + 1
    left = (date(2026, 12, 19) - date.fromisoformat(today)).days

    pad_x, pad_top = 68 * SCALE, 62 * SCALE
    label_w = 250 * SCALE
    content_x = pad_x + label_w + 34 * SCALE
    content_w = W * SCALE - content_x - pad_x

    f_kicker = font(19)
    f_date = font(52, True)
    f_right = font(19, True)
    f_theme = font(25)
    f_label = font(21, True)
    f_body = font(23)
    f_foot = font(19)

    # 先量高度
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    theme_lines = wrap(probe, day["short"], f_theme, W * SCALE - pad_x * 2)
    rows = []
    for it in day["items"]:
        lab = wrap(probe, it["t"], f_label, label_w - 10 * SCALE)
        body = wrap(probe, it["r"], f_body, content_w)
        rows.append((lab, body, max(len(lab), len(body))))

    lh_body = int(23 * SCALE * 1.62)
    lh_label = int(21 * SCALE * 1.5)
    lh_theme = int(25 * SCALE * 1.5)
    head_h = 62 * SCALE + 52 * SCALE + 40 * SCALE + len(theme_lines) * lh_theme
    rows_h = sum(max(r[2] * lh_body, 20 * SCALE) + 40 * SCALE for r in rows)
    foot_h = 30 * SCALE + 20 * SCALE + 2 * int(19 * SCALE * 1.85)
    H = pad_top + head_h + 32 * SCALE + rows_h + foot_h + 56 * SCALE

    img = Image.new("RGB", (W * SCALE, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    y = pad_top

    # 顶部
    d.text((pad_x, y), "考研冲刺 · D%d" % idx, font=f_kicker, fill=GREY)
    y += 40 * SCALE
    d.text((pad_x, y), day["md"], font=f_date, fill=INK)
    d.text((pad_x + d.textlength(day["md"], font=f_date) + 18 * SCALE, y),
           day["wd"], font=f_date, fill=INK)
    ry = pad_top + 8 * SCALE
    d.text((W * SCALE - pad_x - d.textlength("距初试", font=f_right), ry),
           "距初试", font=f_right, fill=RED)
    d.text((W * SCALE - pad_x - d.textlength("%d 天" % left, font=f_right), ry + 30 * SCALE),
           "%d 天" % left, font=f_right, fill=RED)
    y += 52 * SCALE + 18 * SCALE
    for ln in theme_lines:
        d.text((pad_x, y), ln, font=f_theme, fill=GREY2)
        y += lh_theme

    y += 18 * SCALE
    d.line([(pad_x, y), (W * SCALE - pad_x, y)], fill=LINE, width=SCALE)

    # 竖线
    vx = pad_x + label_w
    vtop = y + 10 * SCALE
    vbot = y + 6 * SCALE + rows_h - 10 * SCALE
    d.line([(vx, vtop), (vx, vbot)], fill=(208, 208, 217), width=int(1.5 * SCALE))

    for i, (lab, body, n) in enumerate(rows):
        y += 20 * SCALE
        ly = y + 3 * SCALE
        for ln in lab:
            d.text((pad_x, ly), ln, font=f_label, fill=INK)
            ly += lh_label
        by = y
        for ln in body:
            d.text((content_x, by), ln, font=f_body, fill=INK)
            by += lh_body
        y = max(ly, by) + 20 * SCALE
        if i != len(rows) - 1:
            d.line([(pad_x, y), (W * SCALE - pad_x, y)], fill=LINE2, width=int(1.5 * SCALE))
            y += SCALE

    # 页脚
    y += 30 * SCALE
    d.line([(pad_x, y), (W * SCALE - pad_x, y)], fill=LINE, width=SCALE)
    y += 20 * SCALE
    d.text((pad_x, y), "做到 4 小时，这天就不算废。", font=f_foot, fill=RED)
    y += int(19 * SCALE * 1.85)
    d.text((pad_x, y), "完整计划见打卡页", font=f_foot, fill=GREY)

    WORK.mkdir(parents=True, exist_ok=True)
    out = out or PNG
    img.save(out)
    return day


if __name__ == "__main__":
    import sys
    day_arg = sys.argv[1] if len(sys.argv) > 1 else None
    out_arg = sys.argv[2] if len(sys.argv) > 2 else None
    res = build(day_arg, out_arg)
    print("OK" if res else "NO_PLAN", res["d"] if res else "")

