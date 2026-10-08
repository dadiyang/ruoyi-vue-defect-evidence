# -*- coding: utf-8 -*-
"""A27 取证补拍：接口新建用户（自定义口令）首次登录弹「初始密码」提示实拍。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, '/home/irons/dev/ruoyi-regression')
sys.path.insert(0, '/home/irons/dev/ruoyi-regression/exec')
from api import admin_token, delete, login, one, post, uniq

sys.path.insert(0, os.environ.get('TCMS_ROOT', '/home/irons/dev/tcms'))
from tcms.repro import UiRepro, load_ui_profile

OUT = Path('/home/irons/dev/ruoyi-regression/reports/shots-r1')
PW = 'CustomPw@2026x'

t = admin_token()
un = uniq('a27u')
http, r = post('/system/user', {'userName': un, 'nickName': 'a27probe', 'password': PW, 'status': '0'}, token=t)
assert r.get('code') == 200, r
urow = one("SELECT user_id FROM sys_user WHERE user_name=%s AND del_flag='0'", (un,))
try:
    tok = login(un, PW)
    assert isinstance(tok, str), tok
    rp = UiRepro(load_ui_profile('ruoyi-vue'), tag='A27', out_dir=OUT)
    try:
        rp.page.close()
        ctx = rp.browser.new_context(viewport=rp.p.viewport)
        ctx.add_init_script('document.cookie="Admin-Token="+encodeURIComponent("%s")+"; path=/";' % tok)
        rp.page = ctx.new_page()
        rp.page.set_default_timeout(30000)
        rp.step(1, '以接口新建（已设自定义口令 %s）用户令牌注入登录管理端首页' % PW)
        rp.page.goto(rp.p.web_url + '/index', wait_until='domcontentloaded')
        rp.page.wait_for_timeout(4000)
        box = rp.page.locator('.el-message-box:visible').first
        box.wait_for(state='visible', timeout=8000)
        rp.page.wait_for_timeout(500)
        rp.shot('A27-01-initpwd-prompt.png')
        rp._record('note', '弹窗文案: %s' % box.inner_text().strip()[:200])
    finally:
        rp.close()
finally:
    delete('/system/user/%s' % urow['user_id'], token=t)
print('A27 取证完成', flush=True)
