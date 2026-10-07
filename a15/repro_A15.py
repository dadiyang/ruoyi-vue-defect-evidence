#!/usr/bin/env python3
# A15 复现脚本：停用角色不失效在线会话权限（并对照"编辑角色"路径正常刷新）。
# 追加腿：用户换绑角色同样不刷新旧会话（连 /getInfo 自愈也失效）。
# 用法: /home/irons/dev/tcms/venv/bin/python repro_A15.py
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/irons/dev/ruoyi-regression")
import api

OUT = Path(__file__).resolve().parent
ROLE_KEY = "A15PROLE"
ROLE_NAME = "A15复现角色"
UN = "a15user"
NICK = "A15复现用户"
PW = "Admin123456"


def shot(page, name):
    page.screenshot(path=str(OUT / name), full_page=False)
    print("shot:", name)


def menu_id_by_perms(perms, mtype):
    rows = api.db("select menu_id from sys_menu where perms=%s and menu_type=%s", (perms, mtype))
    assert rows, f"menu not found: {perms}"
    return rows[0]["menu_id"]


def main():
    at = api.admin_token()
    evidence = {}

    # 1) 建测试角色（只授权"参数管理"）
    h, r = api.post("/system/role", token=at, body={
        "roleName": ROLE_NAME, "roleKey": ROLE_KEY, "roleSort": "9",
        "status": "0", "dataScope": "1", "deptIds": [],
        "menuIds": [menu_id_by_perms("system:config:list", "C"),
                    menu_id_by_perms("system:config:query", "F")]})
    assert r.get("code") == 200, r
    h, r = api.get("/system/role/list", token=at, params={"roleKey": ROLE_KEY})
    role_id = r["rows"][0]["roleId"]
    evidence["role_id"] = role_id

    # 2) 建测试用户并绑定该角色
    if api.db("select user_id from sys_user where user_name=%s", (UN,)):
        api.db("delete from sys_user where user_name=%s", (UN,))
    h, r = api.post("/system/user", token=at, body={
        "deptId": 100, "userName": UN, "nickName": NICK, "password": PW,
        "status": "0", "roleIds": [role_id]})
    assert r.get("code") == 200, r
    h, r = api.get("/system/user/list", token=at, params={"userName": UN})
    user_id = r["rows"][0]["userId"]
    evidence["user_id"] = user_id

    # 3) 测试用户登录（验证码从 Redis 读取）
    ut = api.login(UN, PW)
    assert isinstance(ut, str), ut
    evidence["login_ok"] = True

    # 基线：有参数管理权限
    h, r = api.get("/system/config/1", token=ut)
    evidence["before_disable"] = r.get("code")  # 期望 200

    # 4) 停用角色（UI 截图）
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()
        pg.set_default_timeout(20000)
        with pg.expect_response(lambda r: "/captchaImage" in r.url, timeout=20000) as cap_info:
            pg.goto("http://localhost:18091/login", wait_until="domcontentloaded")
        pg.wait_for_selector('input[placeholder="账号"]', timeout=15000)
        uuid = cap_info.value.json().get("uuid")
        ans = api.redis_get("captcha_codes:" + uuid)
        pg.fill('input[placeholder="账号"]', "admin")
        pg.fill('input[placeholder="密码"]', "admin123")
        pg.fill('input[placeholder="验证码"]', ans)
        pg.locator("button", has_text="登 录").first.click()
        pg.wait_for_url("**/index**", timeout=20000)
        pg.goto("http://localhost:18091/system/role", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        shot(pg, "a15_1_role_list.png")
        row = pg.locator("tr", has_text=ROLE_NAME).first
        sw = row.locator(".el-switch").first
        sw.click()
        pg.wait_for_selector(".el-message-box", timeout=5000)
        shot(pg, "a15_2_confirm_disable.png")
        pg.locator(".el-message-box__btns button.el-button--primary").click()
        pg.wait_for_timeout(1500)
        shot(pg, "a15_3_role_disabled.png")
        b.close()

    h, r = api.get("/system/role/list", token=at, params={"roleKey": ROLE_KEY})
    evidence["role_status_after_ui"] = r["rows"][0]["status"]  # 期望 "1"

    # 5) 停用后旧会话直接访问受控接口
    h, r = api.get("/system/config/1", token=ut)
    evidence["after_disable_direct"] = r.get("code")  # 期望 401/403，实际 200
    h, r = api.get("/system/config/list", token=ut, params={"pageNum": 1, "pageSize": 5})
    evidence["after_disable_list"] = r.get("code")  # 实际 200

    # 对照腿：编辑角色收回菜单授权 → 旧会话即时 403（刷新机制在位）
    h, r = api.put("/system/role", token=at, body={
        "roleId": role_id, "roleName": ROLE_NAME, "roleKey": ROLE_KEY,
        "roleSort": "9", "status": "1", "dataScope": "1", "deptIds": [], "menuIds": []})
    assert r.get("code") == 200, r
    h, r = api.get("/system/config/1", token=ut)
    evidence["after_edit_role_direct"] = r.get("code")  # 对照：403 生效
    # 恢复菜单授权（换绑腿需要"有权限"的起点角色）
    h, r = api.put("/system/role", token=at, body={
        "roleId": role_id, "roleName": ROLE_NAME, "roleKey": ROLE_KEY,
        "roleSort": "9", "status": "1", "dataScope": "1", "deptIds": [],
        "menuIds": [menu_id_by_perms("system:config:list", "C"),
                    menu_id_by_perms("system:config:query", "F")]})
    assert r.get("code") == 200, r

    # 换绑腿：把用户从"停用中的角色"换绑到"启用且无菜单授权的角色"
    h, r = api.post("/system/role", token=at, body={
        "roleName": "A15换绑角色", "roleKey": "A15RB", "roleSort": "9",
        "status": "0", "dataScope": "1", "deptIds": [], "menuIds": []})
    assert r.get("code") == 200, r
    h, r = api.get("/system/role/list", token=at, params={"roleKey": "A15RB"})
    rid_b = r["rows"][0]["roleId"]
    evidence["rebind_role_id"] = rid_b
    h, g = api.get("/getInfo", token=ut)
    evidence["step5_getinfo_has_config_query"] = "system:config:query" in set(g.get("permissions", []))
    h, r = api.put("/system/user", token=at, body={
        "userId": user_id, "deptId": 100, "userName": UN, "nickName": NICK,
        "status": "0", "roleIds": [rid_b]})
    assert r.get("code") == 200, r
    h, r = api.get("/system/config/1", token=ut)
    evidence["step6_after_reassign_direct"] = r.get("code")  # 期望 401/403，实际 200
    h, g = api.get("/getInfo", token=ut)
    evidence["step6_getinfo_still_has_perm"] = "system:config:query" in set(g.get("permissions", []))
    h, r = api.get("/system/config/1", token=ut)
    evidence["step6_after_getinfo_direct"] = r.get("code")  # 连 getInfo 自愈也失效=仍 200

    # 对照腿：强退
    h, r = api.get("/monitor/online/list", token=at,
                   params={"username": UN, "pageNum": 1, "pageSize": 50})
    tid = next((it["tokenId"] for it in r.get("rows", []) if it.get("userName") == UN), None)
    evidence["force_logout_token_found"] = tid is not None
    if tid:
        api.delete("/monitor/online/%s" % tid, token=at)
    h, g = api.get("/getInfo", token=ut)
    evidence["step7_after_forcelogout"] = g.get("code")  # 401

    # 清理
    api.db("delete from sys_user where user_name=%s", (UN,))
    api.db("delete from sys_role where role_id=%s", (role_id,))
    api.db("delete from sys_role where role_id=%s", (rid_b,))

    with open(OUT / "a15_evidence.json", "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)
    print("== evidence ==")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
