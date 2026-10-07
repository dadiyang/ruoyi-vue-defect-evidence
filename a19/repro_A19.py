#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A19 复现：菜单编辑上级选择器可选自身子树+后端无环检测→子树从菜单树消失。
API: 种 a19Parent>a19M3>a19M31；UI: 编辑 a19M3，上级选择器出现自身与子菜单，
选 a19M31（其子）为父→保存 200；菜单树三节点全部消失（环致 buildMenuTree 断链）；
DB parent_id 成环。清理删除 a19 系列。"""
import json
import os
import sys
import time

sys.path.insert(0, "/home/irons/dev/ruoyi-regression")
import api  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

OUT = os.environ.get("TCMS_ARTIFACT_DIR", os.path.dirname(os.path.abspath(__file__)))
BASE = "http://localhost:18091"
PARENT, M3, M31 = "a19Parent", "a19M3", "a19M31"


def shot(pg, name):
    pg.screenshot(path=os.path.join(OUT, name), full_page=True)


def find_menu(tok, name):
    _, payload = api.get("/system/menu/list", token=tok, params={"menuName": name})
    rows = [r for r in (payload.get("data") or []) if r["menuName"] == name]
    return rows[0] if rows else None


def treeselect_names(tok):
    _, payload = api.get("/system/menu/treeselect", token=tok)
    tree = payload.get("data") or []

    def walk(nodes, acc):
        for n in nodes:
            acc.add(n["label"])
            walk(n.get("children") or [], acc)
    acc = set()
    walk(tree, acc)
    return acc


def main():
    ev = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    tok = api.admin_token()

    # ---- seed ----
    ids = {}
    pid = 0
    olds = {name: find_menu(tok, name) for name in
            (PARENT, M3, M31, "a19M1", "a19M2")}
    if olds[M3]:
        olds[M3]["parentId"] = 0
        api.put("/system/menu", token=tok, body=olds[M3])
    for name in ("a19M2", M31, M3, "a19M1", PARENT):
        if olds[name]:
            api.delete("/system/menu/%s" % olds[name]["menuId"], token=tok)
    for name in (PARENT, M3, M31):
        _, r = api.post("/system/menu", token=tok, body={
            "menuName": name, "parentId": pid, "orderNum": 1, "path": name,
            "component": None, "query": None, "isFrame": 1, "isCache": 0,
            "menuType": "C", "visible": 0, "status": 0, "perms": None,
            "icon": "#", "remark": None})
        assert r.get("code") == 200, (name, r)
        row = find_menu(tok, name)
        assert row, name
        ids[name] = row["menuId"]
        pid = row["menuId"]
    ev["seed"] = {"ids": ids,
                  "treeselect_has_all3": all(n in treeselect_names(tok)
                                             for n in (PARENT, M3, M31))}

    # ---- UI ----
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()
        pg.set_default_timeout(20000)
        with pg.expect_response(lambda r: "/captchaImage" in r.url,
                                timeout=20000) as cap_info:
            pg.goto(BASE + "/login", wait_until="domcontentloaded")
        pg.wait_for_selector('input[placeholder="账号"]', timeout=15000)
        uuid = cap_info.value.json().get("uuid")
        ans = api.redis_get("captcha_codes:" + uuid)
        pg.fill('input[placeholder="账号"]', "admin")
        pg.fill('input[placeholder="密码"]', "admin123")
        pg.fill('input[placeholder="验证码"]', ans)
        pg.locator("button", has_text="登 录").first.click()
        pg.wait_for_url("**/index**", timeout=20000)
        pg.goto(BASE + "/system/menu", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        pg.locator("button", has_text="展开/折叠").first.click()
        pg.wait_for_timeout(1000)
        shot(pg, "A19_01_menu_tree.png")

        row = pg.locator("tr.el-table__row", has_text=M3).first
        row.locator("button", has_text="修改").first.click()
        pg.wait_for_selector(".el-dialog:visible", timeout=10000)
        pg.wait_for_timeout(1000)
        dlg = pg.locator(".el-dialog:visible").first
        dlg.locator(".el-select__wrapper").first.click()
        pg.wait_for_timeout(1500)
        pop = pg.locator(".el-popper:visible").filter(has_text="主类目").last
        # 树弹层懒渲染：逐级展开 主类目 → a19Parent
        pop.locator(".el-tree-node__content", has_text="主类目").first \
           .locator(".el-tree-node__expand-icon").click()
        pg.wait_for_timeout(800)
        pop.locator(".el-tree-node__content", has_text=PARENT).first \
           .locator(".el-tree-node__expand-icon").click()
        pg.wait_for_timeout(800)
        pop.locator(".el-tree-node__content", has_text=M3).first \
           .locator(".el-tree-node__expand-icon").click()
        pg.wait_for_timeout(800)
        opts = pop.locator(".el-tree-node__content").all_inner_texts()
        ev["ui"] = {"parent_options_visible": [o.strip() for o in opts
                                               if "a19" in o],
                    "self_selectable": any(M3 in o for o in opts),
                    "descendant_selectable": any(M31 in o for o in opts)}
        shot(pg, "A19_02_parent_options.png")

        pop.locator(".el-tree-node__content", has_text=M31).first.click()
        pg.wait_for_timeout(800)
        shot(pg, "A19_03_child_as_parent.png")
        with pg.expect_response(lambda r: r.url.endswith("/system/menu")
                                and r.request.method == "PUT",
                                timeout=15000) as edit_info:
            dlg.get_by_role("button", name="确 定").click()
            pg.wait_for_timeout(2000)
        ev["ui"]["edit_http"] = edit_info.value.status
        try:
            ev["ui"]["edit_body"] = edit_info.value.json()
        except Exception as exc:
            ev["ui"]["edit_body_parse"] = str(exc)[:100]
        pg.wait_for_timeout(2000)
        shot(pg, "A19_04_after_save_tree.png")
        rows = pg.locator("tr.el-table__row").filter(has_text="a19").count()
        ev["ui"]["tree_rows_with_a19_after_save"] = rows
        b.close()

    # ---- verify ----
    names = treeselect_names(tok)
    _, payload = api.get("/system/menu/list", token=tok, params={"menuName": "a19"})
    rows = payload.get("data") or []
    ev["verify"] = {
        "treeselect_has_parent": PARENT in names,
        "treeselect_has_m3": M3 in names,
        "flat_list_rows": len(rows),
        "parent_id_map": {r["menuName"]: r["parentId"] for r in rows},
        "cycle": (rows and ids[M31] == next((r["parentId"] for r in rows
                                             if r["menuName"] == M3), None)),
    }

    # ---- cleanup（先把成环节点挂回正常父，否则有子菜单删不掉）----
    m3_row = find_menu(tok, M3)
    if m3_row:
        m3_row["parentId"] = ids[PARENT]
        m3_row.pop("children", None)
        api.put("/system/menu", token=tok, body=m3_row)
    for name in (M31, M3, PARENT):
        r = find_menu(tok, name)
        if r:
            api.delete("/system/menu/%s" % r["menuId"], token=tok)
    _, payload = api.get("/system/menu/list", token=tok, params={"menuName": "a19"})
    ev["cleanup"] = {"remaining": len(payload.get("data") or [])}
    with open(os.path.join(OUT, "a19_evidence.json"), "w", encoding="utf-8") as f:
        json.dump(ev, f, ensure_ascii=False, indent=1)
    print(json.dumps(ev, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
