# -*- coding: utf-8 -*-
"""QQ 官方机器人 C2C 私聊的公共发送代码（云端和本地共用）。

凭证从环境变量读：QQ_APP_ID / QQ_APP_SECRET / QQ_OPENID
"""
import base64
import json
import os
import urllib.error
import urllib.request

TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
API = "https://api.sgroup.qq.com"


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


def creds():
    app_id = os.environ.get("QQ_APP_ID", "").strip()
    secret = os.environ.get("QQ_APP_SECRET", "").strip()
    openid = os.environ.get("QQ_OPENID", "").strip()
    if not (app_id and secret and openid):
        raise SystemExit("缺环境变量 QQ_APP_ID / QQ_APP_SECRET / QQ_OPENID")
    return app_id, secret, openid


def get_token(app_id, secret):
    d = post(TOKEN_URL, {"appId": app_id, "clientSecret": secret}, {})
    if "access_token" not in d:
        raise SystemExit("取 token 失败: " + json.dumps(d, ensure_ascii=False)[:400])
    return d["access_token"]


def send_text(token, openid, text):
    return post(API + "/v2/users/%s/messages" % openid,
                {"content": text, "msg_type": 0},
                {"Authorization": "QQBot " + token})


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
