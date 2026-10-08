# -*- coding: utf-8 -*-
"""A25/A26 缺陷卡 UI 取证补拍（补证通道，判定已在引擎 R13 job 2376）。
A25：定时任务表单填 65 字符任务名称→界面弹数据库报错原文（管理员可踩面实拍）。
A26：权限字符含逗号的角色授代码生成菜单→非管理员用户界面出现「创建」按钮→点击被拒（口径不一致实拍）。
截图与 timeline 落 reports/shots-r1/。"""
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, '/home/irons/dev/ruoyi-regression')
sys.path.insert(0, '/home/irons/dev/ruoyi-regression/exec')
from api import admin_token, db, delete, get, login, one, post, uniq
from contract_lib import DEFAULT_PW

sys.path.insert(0, os.environ.get('TCMS_ROOT', '/home/irons/dev/tcms'))
from tcms.repro import UiRepro, load_ui_profile

OUT = Path('/home/irons/dev/ruoyi-regression/reports/shots-r1')
LONG_NAME = 'J' * 65


def evidence_a25():
    rp = UiRepro(load_ui_profile('ruoyi-vue'), tag='A25', out_dir=OUT)
    try:
        rp.login_by_token('/monitor/job')
        rp.step(2, '点击「新增」打开新建定时任务对话框')
        rp.page.locator('button', has_text='新增').first.click()
        rp.page.wait_for_selector('.el-dialog:visible', timeout=8000)
        dlg = rp.page.locator('.el-dialog:visible').first
        dlg.locator('.el-form-item', has_text='任务名称').locator('input').first.fill(LONG_NAME)
        dlg.locator('.el-form-item', has_text='调用方法').locator('input').first.fill('ryTask.ryNoParams()')
        dlg.locator('.el-form-item', has_text='cron').locator('input').first.fill('0 0 0 1 1 ? *')
        rp.shot('A25-02-form-65chars.png')
        rp.step(3, '点「确 定」提交（任务名称 65 字符，界面输入框无长度上限）')
        off = rp.log_mark()
        dlg.locator('.el-dialog__footer button', has_text='确').first.click()
        msg = rp.page.locator('.el-message').first
        msg.wait_for(state='visible', timeout=6000)
        rp.page.wait_for_timeout(500)  # 等入场过渡完成（opacity 0 也算 visible，防竞态空拍）
        rp.shot('A25-03-toast-rawdberror.png')
        toast = msg.inner_text().strip()
        rp._record('toast', '界面弹出: ' + toast[:300])
        print('A25 toast=%r' % (toast or '')[:300], flush=True)
        errs = rp.log_errors(off)
        print('A25 日志窗口异常行数=%d 首行=%s' % (len(errs), (errs or [''])[0][:160]), flush=True)
        row = one("SELECT job_id FROM sys_job WHERE job_name=%s", (LONG_NAME,))
        print('A25 库内 65 字符任务名行=%s（500 被数据库拒，未落行）' % row, flush=True)
    finally:
        rp.close()


def evidence_a26():
    t = admin_token()
    # 前置造数：代码生成菜单子树 + 含逗号权限字符角色 + 挂该角色的普通用户
    gen = one("SELECT menu_id FROM sys_menu WHERE menu_name='系统工具' AND menu_type='M'")
    kids = db("SELECT menu_id FROM sys_menu WHERE parent_id=%s", (gen['menu_id'],))
    menu_ids = [gen['menu_id']] + [k['menu_id'] for k in kids]
    rk = uniq('a26k') + ',admin'
    http, r = post('/system/role', {'roleName': uniq('a26role'), 'roleKey': rk, 'roleSort': 9,
                                    'dataScope': '1', 'status': '0', 'menuIds': menu_ids, 'deptIds': []}, token=t)
    assert r.get('code') == 200, r
    rrow = one("SELECT role_id FROM sys_role WHERE role_key=%s AND del_flag='0'", (rk,))
    un = uniq('a26u')
    http, r = post('/system/user', {'userName': un, 'nickName': 'a26probe', 'password': DEFAULT_PW,
                                    'status': '0', 'roleIds': [rrow['role_id']]}, token=t)
    assert r.get('code') == 200, r
    urow = one("SELECT user_id FROM sys_user WHERE user_name=%s AND del_flag='0'", (un,))
    try:
        tok = login(un, DEFAULT_PW)
        assert isinstance(tok, str), tok
        http, gi = get('/getInfo', token=tok)
        print('A26 该用户 getInfo roles=%s perms=%s' % (gi.get('roles'), str(gi.get('permissions'))[:120]), flush=True)
        rp = UiRepro(load_ui_profile('ruoyi-vue'), tag='A26', out_dir=OUT)
        try:
            # 令牌注入该用户会话（取证手段，报告如实标注）
            rp.page.close()
            ctx = rp.browser.new_context(viewport=rp.p.viewport)
            ctx.add_init_script('document.cookie="Admin-Token="+encodeURIComponent("%s")+"; path=/";' % tok)
            rp.page = ctx.new_page()
            rp.page.set_default_timeout(30000)
            rp.step(1, '以挂「含逗号权限字符」角色的普通用户令牌注入直达 代码生成页')
            rp.page.goto(rp.p.web_url + '/tool/gen', wait_until='domcontentloaded')
            rp.page.wait_for_timeout(4000)
            # 接口新建用户 pwd_update_date 为空触发「初始密码」安全提示弹窗，先点「取消」关闭再取证
            box = rp.page.locator('.el-message-box:visible').first
            if box.count() > 0 and box.is_visible():
                rp._record('note', '界面弹「安全提示：初始密码」弹窗（接口新建用户 pwd_update_date 为空所致），点取消关闭')
                box.locator('.el-message-box__btns button', has_text='取').first.click()
                rp.page.wait_for_timeout(800)
            rp.shot('A26-01-gen-page-create-btn.png')
            btn = rp.page.locator('button', has_text='创建').first
            visible = btn.count() > 0 and btn.is_visible()
            print('A26 「创建」按钮可见=%s（该用户并非管理员，判定端不认其角色）' % visible, flush=True)
            rp.step(2, '点击界面显示的「创建」按钮（v-hasRole=admin 放行显示）')
            btn.click()
            rp.page.wait_for_selector('.el-dialog:visible', timeout=8000)
            dlg = rp.page.locator('.el-dialog:visible').first
            dlg.locator('textarea').first.fill('CREATE TABLE t_a26_probe (id INT)')
            rp.step(3, '填建表 SQL 点「确 定」（后端 hasRole 按整串比较，应拒）')
            dlg.locator('.el-dialog__footer button', has_text='确').first.click()
            msg2 = rp.page.locator('.el-notification').first  # 403 走 ElNotification（request.js 分流）
            msg2.wait_for(state='visible', timeout=6000)
            rp.page.wait_for_timeout(500)
            rp.shot('A26-02-create-denied.png')
            toast = msg2.inner_text().strip()
            rp._record('toast', '界面弹出: ' + toast[:200])
            print('A26 toast=%r' % (toast or '')[:200], flush=True)
            rows = db("SELECT table_name FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='t_a26_probe'")
            print('A26 建表是否落库=%s（判定端拒绝，未落）' % bool(rows), flush=True)
        finally:
            rp.close()
    finally:
        delete('/system/user/%s' % urow['user_id'], token=t)
        delete('/system/role/%s' % rrow['role_id'], token=t)


only = set(sys.argv[1:])
for tag, fn in (('A25', evidence_a25), ('A26', evidence_a26)):
    if only and tag not in only:
        continue
    print('== %s ==' % tag, flush=True)
    try:
        fn()
    except Exception:
        traceback.print_exc()
print('取证完成', flush=True)
