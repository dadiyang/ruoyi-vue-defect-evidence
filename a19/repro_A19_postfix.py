"""A19 修后实拍：菜单编辑界面上级树下拉不再出现自身与子孙（换包窗口内跑）。"""
import json
import time
import os
import sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, '/home/irons/dev/ruoyi-regression')
sys.path.insert(0, '/home/irons/dev/ruoyi-regression/exec')
import api
from api import post, one, uniq, delete as api_delete

def delete_menu(menu_id):
    return api_delete('/system/menu/%s' % menu_id, token=api.admin_token(), kind='清场')[1].get('code')

BASE = "http://127.0.0.1:18091"
SHOT = "/tmp/opencode/a19-postfix"
os.makedirs(SHOT, exist_ok=True)

# 现造三层菜单 P > M > MC，编辑 M 打开上级树
def ensure_menu(tag, parent_id=0, menu_type='C'):
    name = uniq('menu_' + tag)
    path = uniq('rt' + tag)
    body = {'parentId': parent_id, 'menuName': name, 'orderNum': 1, 'path': path,
            'component': 'system/test/index' if menu_type == 'C' else '',
            'menuType': menu_type, 'visible': '0', 'status': '0',
            'perms': '', 'icon': '#', 'isFrame': '1', 'isCache': '0'}
    _, r = post('/system/menu', body, token=api.admin_token(), kind='造菜单')
    assert r.get('code') == 200, r
    return one("SELECT menu_id FROM sys_menu WHERE menu_name=%s", (name,))['menu_id'], name

p_id, pname = ensure_menu('a19pfP', menu_type='M')
m_id, mname = ensure_menu('a19pfM', parent_id=p_id)
mc_id, mcname = ensure_menu('a19pfMC', parent_id=m_id)

ev = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "build": "fix/a19-menu-cycle-check@da385ca + ui@a2cd198"}
try:
    # API 腿：移入自身子孙被拒
    src = api.one("SELECT menu_name, path, component FROM sys_menu WHERE menu_id=%s", (m_id,))
    _, r = api.put('/system/menu', {'menuId': m_id, 'parentId': mc_id, 'menuName': src['menu_name'],
                                    'menuType': 'C', 'orderNum': 1, 'path': src['path'],
                                    'component': src['component'], 'visible': '0', 'status': '0',
                                    'perms': '', 'icon': '#', 'isFrame': '1', 'isCache': '0'},
                   token=api.admin_token(), kind='移入自身子孙(修后)')
    ev["api_reject"] = r
    assert r.get('code') != 200, r

    # UI 腿：编辑 M，打开上级菜单树选择器，截图树内容
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_context(viewport={'width': 1440, 'height': 900}).new_page()
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
        pg.wait_for_timeout(2000)
        pg.goto("http://localhost:18091/system/menu", wait_until="domcontentloaded")
        pg.wait_for_timeout(2500)
        pg.evaluate("document.querySelectorAll('input[type=search]').forEach(i => i.value = '')")
        pg.locator("input[placeholder='请输入菜单名称']").first.fill(mname)
        pg.locator("button:has-text('搜索')").first.click()
        pg.wait_for_timeout(2000)
        row = pg.locator("tr", has_text=mname).first
        row.locator("button:has-text('修改')").first.click()
        pg.wait_for_timeout(800)
        pg.locator(".el-dialog, .el-drawer").locator("label:has-text('上级菜单')").locator("xpath=following-sibling::div//input").first.click(force=True)
        pg.wait_for_timeout(1500)
        popper = pg.locator(".el-select__popper:visible").last
        popper.locator(".el-tree-node__expand-icon").first.click()
        pg.wait_for_timeout(1200)
        tree = popper.locator(".el-tree").last
        txt = tree.inner_text()
        ev["tree_contains_self"] = mname in txt
        ev["tree_contains_child"] = mcname in txt
        ev["tree_contains_parent"] = pname in txt
        pg.screenshot(path=f"{SHOT}/a19-postfix-tree-exclude.png")
        assert not ev["tree_contains_self"], txt
        assert not ev["tree_contains_child"], txt
        assert ev["tree_contains_parent"], txt
        b.close()
    with open(f"{SHOT}/a19_postfix_evidence.json", "w") as f:
        json.dump(ev, f, ensure_ascii=False, indent=1)
    print(json.dumps(ev, ensure_ascii=False))
finally:
    delete_menu(mc_id); delete_menu(m_id); delete_menu(p_id)
