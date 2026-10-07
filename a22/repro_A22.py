#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A22 复现：重置密码/自助改密接口无 5-20 口令长度闸门——写入登录门范围外口令后，
该口令（完全正确）永远无法登录且文案误导。对照腿 5 字符可正常登录。用后清理。"""
import json
import os
import sys
import time

sys.path.insert(0, "/home/irons/dev/ruoyi-regression")
sys.path.insert(0, "/home/irons/dev/ruoyi-regression/exec")
import api  # noqa: E402
from contract_lib import ensure_user, delete_user, user_token, DEFAULT_PW  # noqa: E402

OUT = os.environ.get("TCMS_ARTIFACT_DIR", os.path.dirname(os.path.abspath(__file__)))


def main():
    ev = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    uid, uname = ensure_user("a22r")
    ev["user"] = {"username": uname, "len": len(uname)}
    t = api.admin_token()
    legs = []
    # 自助腿（口令仍为 DEFAULT_PW）
    utok = user_token(uname)
    h, r = api.put("/system/user/profile/updatePwd",
                   {"oldPassword": DEFAULT_PW, "newPassword": "1234"},
                   token=utok, kind="PUT /system/user/profile/updatePwd(4字符)")
    res = api.login(uname, "1234")
    legs.append({"leg": "self_updatePwd_4ch", "write_http": h, "write": r,
                 "login": res[1] if isinstance(res, tuple) else "TOKEN_OK"})
    for pw, tag in (("1", "1ch"), ("x" * 30, "30ch")):
        h, r = api.put("/system/user/resetPwd", {"userId": uid, "password": pw},
                       token=t, kind="PUT /system/user/resetPwd(%s)" % tag)
        res = api.login(uname, pw)
        legs.append({"leg": "resetPwd_" + tag, "write_http": h, "write": r,
                     "login": res[1] if isinstance(res, tuple) else "TOKEN_OK"})
    # 对照腿：5 字符（登录门内）
    h, r = api.put("/system/user/resetPwd", {"userId": uid, "password": "abcde"},
                   token=t, kind="PUT /system/user/resetPwd(5字符对照)")
    res = api.login(uname, "abcde")
    legs.append({"leg": "resetPwd_5ch_control", "write_http": h, "write": r,
                 "login": "TOKEN_OK" if isinstance(res, str) else res[1]})
    ev["legs"] = legs
    time.sleep(1.5)
    ev["logininfor_last"] = api.db(
        "SELECT status, msg FROM sys_logininfor WHERE user_name=%s AND status='1' ORDER BY info_id DESC LIMIT 1",
        (uname,))
    delete_user(uid)
    ev["cleanup"] = {"user_remaining": len(api.db(
        "SELECT 1 FROM sys_user WHERE user_id=%s AND del_flag='0'", (uid,)))}
    with open(os.path.join(OUT, "a22_evidence.json"), "w", encoding="utf-8") as f:
        json.dump(ev, f, ensure_ascii=False, indent=1)
    print(json.dumps(ev, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
