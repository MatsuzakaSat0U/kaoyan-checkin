# -*- coding: utf-8 -*-
"""午/晚三次成果自检：把该时段的计划条目捞出来，问一句做完了没。

用法：
    python checkin.py morning            # 中午 12:00 问上午
    python checkin.py afternoon          # 18:00 问下午
    python checkin.py evening            # 22:00 问晚上 + 全天收尾
    python checkin.py morning --dry      # 只打印不发
    python checkin.py morning 2026-11-24 # 指定日期
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import qqapi  # noqa: E402

DATA = HERE / "plan_days.json"
if not DATA.exists():
    DATA = HERE.parent / "plan_days.json"

BJT = timezone(timedelta(hours=8))
ORDER = ["morning", "afternoon", "evening"]
LABEL = {"morning": "上午", "afternoon": "下午", "evening": "晚上"}
CLOCK = {"morning": "12:00", "afternoon": "18:00", "evening": "22:00"}
TIME = re.compile(r"^(\d{1,2})\s*[:：]\s*(\d{2})")


def slot_of(t):
    t = t.strip()
    m = TIME.match(t)
    if m:
        h = int(m.group(1))
        return "morning" if h < 12 else ("afternoon" if h < 18 else "evening")
    head = t.split()[0] if t.split() else t
    if head in ("上午", "白天", "早", "早上"):
        return "morning"
    if head in ("中午", "午休", "下午"):
        return "afternoon"
    return "evening"


def next_start(day, slot):
    """紧邻的下一段最早钟点；下一段没安排就返回 None（跨到半夜不算）。"""
    i = ORDER.index(slot)
    if i + 1 >= len(ORDER):
        return None
    s = ORDER[i + 1]
    ts = [TIME.match(it["t"].strip()).group(0)
          for it in day["items"] if slot_of(it["t"]) == s and TIME.match(it["t"].strip())]
    return min(ts) if ts else None


REST_WORDS = ("不学习", "休息", "睡够", "洗澡", "回程")


def build(day, slot):
    items = [(it["t"].strip(), it["r"].strip()) for it in day["items"]
             if slot_of(it["t"]) == slot]
    if not items:
        return None

    if slot == "evening":
        title = "【22:00 全天收尾】%s %s" % (day["md"], day["wd"])
    else:
        title = "【%s %s成果】%s %s" % (CLOCK[slot], LABEL[slot], day["md"], day["wd"])
    lines = [title, ""]

    for t, r in items:
        lines.append(t)
        lines.append("  " + r)
        lines.append("")

    resty = any(any(w in r for w in REST_WORDS) for _, r in items)

    if slot == "evening":
        if resty:
            lines.append("今天按计划休息，不动脑子也是进度。")
            lines.append("早点睡，明天按新计划走。")
        else:
            lines.append("今天一共做了几小时？")
            lines.append("到 4 小时，这天就不算废。")
            lines.append("睡前把明天要翻的书放桌上。")
    elif resty:
        lines.append("这一段本来就不是硬任务，做过就算。")
        lines.append("别给自己追加，留力气给晚上。")
    else:
        nxt = next_start(day, slot)
        lines.append("做完了吗？")
        if nxt:
            lines.append("做完了 → %s 照计划开下一段" % nxt)
            lines.append("没做完 → %s 先补 40 分钟，别顺延" % nxt)
        else:
            lines.append("做完了 → 今天收工，别再翻新的")
            lines.append("没做完 → 睡前补 40 分钟，别拖到明天")
    return "\n".join(lines).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slot", choices=ORDER)
    ap.add_argument("date", nargs="?", default=None)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    d = date.fromisoformat(a.date) if a.date else datetime.now(BJT).date()
    days = json.loads(DATA.read_text(encoding="utf-8"))
    day = next((x for x in days if x["d"] == d.isoformat()), None)
    if not day:
        print("NO_PLAN %s 不在计划表里" % d)
        sys.exit(1)

    text = build(day, a.slot)
    if not text:
        print("NO_SLOT %s 没有 %s 的条目，跳过" % (d, LABEL[a.slot]))
        return

    if a.dry:
        print(text)
        return

    app_id, secret, openid = qqapi.creds()
    token = qqapi.get_token(app_id, secret)
    r = qqapi.send_text(token, openid, text)
    ok = "id" in r or r.get("code") == 0
    print(("已发送 %s %s " % (d, a.slot)) + json.dumps(r, ensure_ascii=False)[:200])
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
