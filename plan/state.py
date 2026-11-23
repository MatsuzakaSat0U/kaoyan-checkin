# -*- coding: utf-8 -*-
"""记录当天哪些时点已经发过，避免冗余 cron 重复推送。

状态存在仓库 _state/<date>.json，用 GITHUB_TOKEN 读写。
没有 token（本地跑）时退化成不记录，不会报错。
"""
import base64
import json
import os
import urllib.error
import urllib.request

API = "https://api.github.com"
REPO = os.environ.get("GITHUB_REPOSITORY", "").strip()
TOK = os.environ.get("GITHUB_TOKEN", "").strip()
BRANCH = "main"


def _url(day):
    return "%s/repos/%s/contents/_state/%s.json" % (API, REPO, day)


def _headers(extra=None):
    h = {"Authorization": "Bearer " + TOK,
         "Accept": "application/vnd.github+json",
         "User-Agent": "kaoyan-plan-bot"}
    if extra:
        h.update(extra)
    return h


def enabled():
    return bool(REPO and TOK)


def load(day):
    if not enabled():
        return {}
    try:
        req = urllib.request.Request(_url(day), headers=_headers())
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode())
        raw = base64.b64decode(d.get("content", "")).decode("utf-8", "ignore")
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def save(day, data):
    """写回状态；失败只打印，不影响已经发出去的消息。"""
    if not enabled():
        return False
    sha = None
    try:
        req = urllib.request.Request(_url(day), headers=_headers())
        with urllib.request.urlopen(req, timeout=20) as r:
            sha = json.loads(r.read().decode()).get("sha")
    except Exception:
        pass
    payload = {"message": "state: " + day,
               "content": base64.b64encode(
                   json.dumps(data, ensure_ascii=False).encode("utf-8")).decode(),
               "branch": BRANCH}
    if sha:
        payload["sha"] = sha
    req = urllib.request.Request(
        _url(day), data=json.dumps(payload).encode(),
        headers=_headers({"Content-Type": "application/json"}), method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=20):
            return True
    except urllib.error.HTTPError as e:
        print("state 写入失败:", e.code,
              e.read().decode("utf-8", "ignore")[:200])
        return False
