#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A11 增补复现：Excel 导入腿（管理端界面）——导入 25 字符账号报"全部导入成功"并入库，
该账号随后登录被前置校验拒绝且文案误导为口令错误。UI 导入 + UI 登录失败实拍 + API/DB 佐证。用后清理。"""
import io
import json
import os
import sys
import time

sys.path.insert(0, "/home/irons/dev/ruoyi-regression")
sys.path.insert(0, "/home/irons/dev/ruoyi-regression/exec")
import api  # noqa: E402
from api import uniq  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

OUT = os.environ.get("TCMS_ARTIFACT_DIR", os.path.dirname(os.path.abspath(__file__)))
UI = "http://localhost:18091"
uname = ("a11imp" + uniq("") + "x" * 25)[:25]
assert len(uname) == 25, uname


def xlsx_bytes():
    wb = Workbook()
    ws = wb.active
    ws.append(["登录名称", "用户名称", "用户邮箱", "手机号码", "部门编号", "账号状态"])
    ws.append([uname, "a11导入", "a11@example.com", "13800000000", 100, "正常"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def shot(pg, name):
    pg.screenshot(path=os.path.join(OUT, name), full_page=True)


def main():
    ev = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "username": uname, "len": len(uname)}
    tok = api.admin_token()
    buf = xlsx_bytes()
    with open(os.path.join(OUT, "a11_import_row.xlsx"), "wb") as f:
        f.write(buf.getvalue())

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()
        pg.set_default_timeout(20000)
        # ---- admin 登录 ----
        with pg.expect_response(lambda x: "/captchaImage" in x.url) as cap:
            pg.goto(UI + "/login", wait_until="domcontentloaded")
        pg.wait_for_selector('input[placeholder="账号"]')
        ans = api.redis_get("captcha_codes:" + cap.value.json().get("uuid"))
        pg.fill('input[placeholder="账号"]', "admin")
        pg.fill('input[placeholder="密码"]', "admin123")
        pg.fill('input[placeholder="验证码"]', ans)
        pg.locator("button", has_text="登 录").first.click()
        pg.wait_for_url("**/index**", timeout=20000)
        pg.wait_for_timeout(2000)
        box = pg.locator(".el-overlay-message-box")
        if box.count():
            box.get_by_role("button", name="取消").click()
            pg.wait_for_timeout(600)
        # ---- 用户管理 → 导入对话框上传 xlsx ----
        pg.goto(UI + "/system/user", wait_until="domcontentloaded")
        pg.wait_for_timeout(2000)
        pg.locator("button", has_text="导入").first.click()
        pg.wait_for_timeout(1200)
        pg.locator("input[type=file]").first.set_input_files(
            os.path.join(OUT, "a11_import_row.xlsx"))
        with pg.expect_response(lambda x: "/system/user/importData" in x.url) as imp:
            pg.locator(".el-dialog:visible").get_by_role("button", name="确 定").click()
            pg.wait_for_timeout(3000)
        ev["import_resp"] = imp.value.json()
        pg.wait_for_timeout(1200)
        shot(pg, "A11_02_import_success.png")
        # ---- DB 佐证入库 ----
        row = api.one("SELECT user_id FROM sys_user WHERE user_name=%s AND del_flag='0'", (uname,))
        ev["db_row"] = row
        # ---- 退出后以导入账号登录（正确初始口令 admin123）→ 误导报错实拍 ----
        pg.goto(UI + "/logout" if False else UI + "/index")  # 直接换 context 更稳
        ctx2 = b.new_context(viewport={"width": 1440, "height": 900})
        pg2 = ctx2.new_page()
        pg2.set_default_timeout(20000)
        with pg2.expect_response(lambda x: "/captchaImage" in x.url) as cap2:
            pg2.goto(UI + "/login", wait_until="domcontentloaded")
        pg2.wait_for_selector('input[placeholder="账号"]')
        ans2 = api.redis_get("captcha_codes:" + cap2.value.json().get("uuid"))
        pg2.fill('input[placeholder="账号"]', uname)
        pg2.fill('input[placeholder="密码"]', "admin123")
        pg2.fill('input[placeholder="验证码"]', ans2)
        pg2.locator("button", has_text="登 录").first.click()
        pg2.wait_for_timeout(2500)
        msg = pg2.locator(".el-message").first.inner_text() if pg2.locator(".el-message").count() else None
        ev["login_ui_toast"] = msg
        ev["login_still_on"] = "/login" in pg2.url
        shot(pg2, "A11_03_login_misleading.png")
        b.close()

    time.sleep(1.5)
    lf = api.db("SELECT status, msg FROM sys_logininfor WHERE user_name=%s ORDER BY info_id DESC LIMIT 1", (uname,))
    ev["logininfor"] = lf
    # ---- cleanup ----
    if row:
        api.delete("/system/user/%s" % row["user_id"], token=tok)
    ev["cleanup"] = {"user_remaining": len(api.db(
        "SELECT 1 FROM sys_user WHERE user_name=%s AND del_flag='0'", (uname,)))}

    with open(os.path.join(OUT, "a11_import_evidence.json"), "w", encoding="utf-8") as f:
        json.dump(ev, f, ensure_ascii=False, indent=1)
    print(json.dumps(ev, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
