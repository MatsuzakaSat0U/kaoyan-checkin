# -*- coding: utf-8 -*-
"""GitHub Actions 版：电脑关机时也能把当天计划发到 QQ 私聊。

与本地 push_qq.py 的差别只有两点：
1. 只发文字（Ubuntu runner 没中文字体，画图要额外装字体）
2. 计划表从仓库里的 plan_days.json 读，凭证从环境变量读

环境变量：QQ_APP_ID / QQ_APP_SECRET / QQ_OPENID
用法：
    python send.py            # 发今天
    python send.py --dry      # 只打印，不发
    python send.py 2026-11-25 # 发指定日期（补发/测试用）
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "plan_days.json"
TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
API = "https://api.sgroup.qq.com"
BJT = timezone(timedelta(hours=8))
EXAM = date(2026, 12, 19)


def today_bj():
    return datetime.now(BJT).date()


def find_day(days, d):
    return next((x for x in days if x["d"] == d), None)


def render(days, day, d):
    idx = [x["d"] for x in days].index(d.isoformat()) + 1
    left = (EXAM - d).days
    out = ["考研冲刺 · D%d" % idx,
           "%s %s · 距初试 %d 天" % (day["md"], day["wd"], left),
           "————————",
           day["short"],
           ""]
    for it in day["items"]:
        t = it["t"].strip()
        r = it["r"].strip()
        head = t.split(" ", 1)[0]
        if " " in t and head[:1].isdigit():
            # "08:30–11:30 数学"：时间和科目分两行
            out.append(t)
            out.append("  " + r)
        else:
            # "07:00–07:20" / "穿插"：标签和内容并成一行
            out.append("%s  %s" % (t, r))
        out.append("")
    out.append("————————")
    out.append("做到 4 小时，这天就不算废。")
    return "\n".join(out)


def post(url, payload, headers, timeout=60):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=dict({"Content-Type": "application/json"}, **headers),
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


def send_text(token, openid, text):
    return post(API + "/v2/users/%s/messages" % openid,
                {"content": text, "msg_type": 0},
                {"Authorization": "QQBot " + token})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date", nargs="?", default=None)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    d = date.fromisoformat(a.date) if a.date else today_bj()
    days = json.loads(DATA.read_text(encoding="utf-8"))
    day = find_day(days, d.isoformat())
    if not day:
        print("NO_PLAN %s 不在计划表里" % d)
        sys.exit(1)

    text = render(days, day, d)
    if a.dry:
        print(text)
        return

    app_id = os.environ.get("QQ_APP_ID", "").strip()
    secret = os.environ.get("QQ_APP_SECRET", "").strip()
    openid = os.environ.get("QQ_OPENID", "").strip()
    if not (app_id and secret and openid):
        raise SystemExit("缺环境变量 QQ_APP_ID / QQ_APP_SECRET / QQ_OPENID")

    token = get_token(app_id, secret)
    r = send_text(token, openid, text)
    ok = "id" in r or r.get("code") == 0
    print(("已发送 %s " % d) + json.dumps(r, ensure_ascii=False)[:300])
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
