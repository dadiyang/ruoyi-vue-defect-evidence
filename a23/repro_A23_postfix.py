"""A23 修后实拍：新增参数表单「系统内置」默认选「否」，新建参数 config_type='N' 可删；显式建 'Y' 仍被拦（CONF-10 防线不回归）。"""
import json
import os
import sys
import time

sys.path.insert(0, "/home/irons/dev/ruoyi-regression")
sys.path.insert(0, "/home/irons/dev/ruoyi-regression/exec")
import api  # noqa: E402
from api import one, uniq  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

OUT = "/tmp/opencode/a23-postfix"
os.makedirs(OUT, exist_ok=True)
key = uniq("a23pf")
ev = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "build": "RuoYi-Vue3 fix/a23-config-default-not-built-in@bae3b27"}
did = None
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        pg.set_default_timeout(15000)
        with pg.expect_response(lambda x: "/captchaImage" in x.url) as cap:
            pg.goto("http://localhost:18091/login", wait_until="domcontentloaded")
        pg.wait_for_selector('input[placeholder="账号"]')
        uuid = cap.value.json().get("uuid")
        ans = api.redis_get("captcha_codes:" + uuid)
        pg.fill('input[placeholder="账号"]', "admin")
        pg.fill('input[placeholder="密码"]', "admin123")
        pg.fill('input[placeholder="验证码"]', ans)
        pg.locator("button", has_text="登 录").first.click()
        pg.wait_for_url("**/index**", timeout=20000)
        pg.goto("http://localhost:18091/system/config", wait_until="domcontentloaded")
        pg.wait_for_timeout(2000)
        pg.locator("button:has-text('新增')").first.click()
        pg.wait_for_timeout(900)
        dlg = pg.locator(".el-dialog", has_text="添加")
        # 默认单选状态：修后应为「否」选中
        radios = dlg.locator(".el-radio-group").first
        ev["default_radio_text"] = radios.inner_text().replace("\n", "")
        ev["default_is_no"] = "否" in (radios.locator(".el-radio.is-checked").inner_text() if radios.locator(".el-radio.is-checked").count() else "")
        pg.screenshot(path=f"{OUT}/a23-postfix-default-no.png")
        dlg.locator('input[placeholder="请输入参数名称"]').first.fill(key)
        dlg.locator('input[placeholder="请输入参数键名"]').first.fill(key)
        dlg.locator('textarea[placeholder="请输入参数键值"]').first.fill("1")
        dlg.locator("button:has-text('确 定')").first.click()
        pg.wait_for_timeout(1500)
        b.close()
    row = one("SELECT config_id, config_type FROM sys_config WHERE config_key=%s", (key,))
    ev["db_config_type"] = row["config_type"]
    did = row["config_id"]
    _, r = api.delete("/system/config/%s" % did, token=api.admin_token(), kind="删除界面新建参数(修后)")
    ev["delete_ui_created"] = {"code": r.get("code"), "msg": r.get("msg")}
    assert ev["default_is_no"], ev
    assert row["config_type"] == "N", row
    assert r.get("code") == 200, r
    did = None
    # CONF-10 防线不回归：显式 configType='Y' 建的参数仍不可删
    _, r2 = api.post("/system/config", token=api.admin_token(), body={
        "configName": key + "Y", "configKey": key + "Y", "configValue": "1", "configType": "Y"})
    row2 = one("SELECT config_id FROM sys_config WHERE config_key=%s", (key + "Y",))
    try:
        _, r3 = api.delete("/system/config/%s" % row2["config_id"], token=api.admin_token(), kind="删内置参数(应被拦)")
        ev["delete_built_in_blocked"] = {"code": r3.get("code"), "msg": r3.get("msg")}
        assert r3.get("code") != 200, r3
    finally:
        api.db("DELETE FROM sys_config WHERE config_id=%s", (row2["config_id"],))
finally:
    if did:
        api.db("DELETE FROM sys_config WHERE config_id=%s", (did,))
with open(f"{OUT}/a23_postfix_evidence.json", "w") as f:
    json.dump(ev, f, ensure_ascii=False, indent=1)
print(json.dumps(ev, ensure_ascii=False))
