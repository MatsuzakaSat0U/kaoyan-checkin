# -*- coding: utf-8 -*-
"""云端兜底：在 GitHub Actions 上画计划卡并发到 QQ 私聊。

和本地 push_qq.py 同一套画法（card_pil），差别：
- 字体走候选列表，云端靠 apt 装 Noto CJK
- 凭证从环境变量读：QQ_APP_ID / QQ_APP_SECRET / QQ_OPENID

用法：
    python send.py            # 画图并发送今天
    python send.py --dry      # 只画图，打印路径
    python send.py --text     # 发纯文字（图发不出去时的退路）
    python send.py 2026-11-25 # 指定日期（补发/测试）
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import card_pil  # noqa: E402

DATA = card_pil.DATA
PNG = card_pil.PNG
TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
API = "https://api.sgroup.qq.com"
BJT = timezone(timedelta(hours=8))
EXAM = date(2026, 12, 19)


def today_bj():
    return datetime.now(BJT).date()


def find_day(days, d):
    return next((x for x in days if x["d"] == d), None)


def render_text(days, day, d):
    """--text 模式用的纯文本版。"""
    idx = [x["d"] for x in days].index(d.isoformat()) + 1
    left = (EXAM - d).days
    out = ["考研冲刺 · D%d" % idx,
           "%s %s · 距初试 %d 天" % (day["md"], day["wd"], left),
           "————————",
           day["short"],
           ""]
    for it in day["items"]:
        t = it["t"].strip()
        head = t.split(" ", 1)[0]
        if " " in t and head[:1].isdigit():
            out.append(t)
            out.append("  " + it["r"].strip())
        else:
            out.append("%s  %s" % (t, it["r"].strip()))
        out.append("")
    out.append("————————")
    out.append("做到 4 小时，这天就不算废。")
    return "\n".join(out)


def post(url, payload, headers, timeout=60):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:600]
        raise SystemExit("HTTP %s %s\n%s" % (e.code, url, body))


def get_token(app_id, secret):
    d = post(TOKEN_URL, {"appId": app_id, "clientSecret": secret}, {})
    if "access_token" not in d:
        raise SystemExit("取 token 失败: " + json.dumps(d, ensure_ascii=False)[:400])
    return d["access_token"]


def send_image(token, openid, png, caption):
    up = post(API + "/v2/users/%s/files" % openid,
              {"file_type": 1,
               "file_data": base64.b64encode(png.read_bytes()).decode(),
               "srv_send_msg": False},
              {"Authorization": "QQBot " + token})
    info = up.get("file_info")
    if not info:
        raise SystemExit("图片上传失败: " + json.dumps(up, ensure_ascii=False)[:400])
    return post(API + "/v2/users/%s/messages" % openid,
                {"content": caption, "msg_type": 7, "media": {"file_info": info}},
                {"Authorization": "QQBot " + token})


def send_text(token, openid, text):
    return post(API + "/v2/users/%s/messages" % openid,
                {"content": text, "msg_type": 0},
                {"Authorization": "QQBot " + token})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date", nargs="?", default=None)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--text", action="store_true")
    a = ap.parse_args()

    d = date.fromisoformat(a.date) if a.date else today_bj()
    days = json.loads(DATA.read_text(encoding="utf-8"))
    day = find_day(days, d.isoformat())
    if not day:
        print("NO_PLAN %s 不在计划表里" % d)
        sys.exit(1)

    left = (EXAM - d).days
    caption = "距初试 %d 天 · %s %s" % (left, day["md"], day["wd"])

    if a.text:
        if a.dry:
            print(render_text(days, day, d))
            return
        body, image = render_text(days, day, d), None
    else:
        if not card_pil.build(d.isoformat()):
            print("NO_PLAN 卡片没生成出来 %s" % d)
            sys.exit(1)
        if a.dry:
            from PIL import Image
            w, h = Image.open(PNG).size
            print("DRY png=%s %.1fKB %dx%d" % (PNG, PNG.stat().st_size / 1024, w, h))
            return
        body, image = caption, PNG
        print("卡片: %dx%d 字体=%s" % (*Image.open(PNG).size, Path(card_pil.REG).name))

    app_id = os.environ.get("QQ_APP_ID", "").strip()
    secret = os.environ.get("QQ_APP_SECRET", "").strip()
    openid = os.environ.get("QQ_OPENID", "").strip()
    if not (app_id and secret and openid):
        raise SystemExit("缺环境变量 QQ_APP_ID / QQ_APP_SECRET / QQ_OPENID")

    token = get_token(app_id, secret)
    r = (send_text(token, openid, body) if image is None
         else send_image(token, openid, image, body))
    ok = "id" in r or r.get("code") == 0
    print(("已发送 %s " % d) + json.dumps(r, ensure_ascii=False)[:300])
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
