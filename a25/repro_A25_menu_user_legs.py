# -*- coding: utf-8 -*-
"""A25 补拍：菜单路由名称 51 字符、用户备注 501 字符两腿的界面实拍（覆盖表要求）。"""
import os
import sys
import traceback

sys.path.insert(0, '/home/irons/dev/ruoyi-regression')
sys.path.insert(0, '/home/irons/dev/ruoyi-regression/exec')
from api import admin_token, db, one, uniq

sys.path.insert(0, os.environ.get('TCMS_ROOT', '/home/irons/dev/tcms'))
from tcms.repro import UiRepro, load_ui_profile

OUT = '/home/irons/dev/ruoyi-regression/reports/shots-r1'
t = admin_token()


def leg_menu():
    name = uniq('a25m')
    rp = UiRepro(load_ui_profile('ruoyi-vue'), tag='A25', out_dir=OUT)
    try:
        rp.login_by_token('/system/menu')
        rp.step(2, '点「新增」打开新增菜单对话框，菜单类型选「菜单」')
        rp.page.locator('button', has_text='新增').first.click()
        rp.page.wait_for_selector('.el-dialog:visible', timeout=8000)
        dlg = rp.page.locator('.el-dialog:visible').first
        dlg.locator('.el-radio', has_text='菜单').first.click()
        dlg.locator('.el-form-item', has_text='菜单名称').locator('input').first.fill(name)
        dlg.locator('.el-form-item', has_text='路由地址').locator('input').first.fill('a25probe')
        dlg.locator('.el-form-item', has_text='路由名称').locator('input').first.fill('R' * 51)
        dlg.locator('.el-form-item', has_text='显示排序').locator('input').first.fill('1')
        rp.shot('A25-04-menu-form-routename51.png')
        rp.step(3, '点「确 定」提交（路由名称 51 字符，界面输入框无长度上限）')
        off = rp.log_mark()
        dlg.locator('.el-dialog__footer button', has_text='确').first.click()
        msg = rp.page.locator('.el-message').first
        msg.wait_for(state='visible', timeout=6000)
        rp.page.wait_for_timeout(500)
        rp.shot('A25-05-menu-toast-rawdberror.png')
        rp._record('toast', '界面弹出: ' + msg.inner_text().strip()[:200])
        row = one("SELECT menu_id FROM sys_menu WHERE menu_name=%s", (name,))
        print('菜单腿 toast=%r 库内行=%s' % (msg.inner_text()[:80], row), flush=True)
    finally:
        rp.close()


def leg_user():
    un = uniq('a25u')
    rp = UiRepro(load_ui_profile('ruoyi-vue'), tag='A25', out_dir=OUT)
    try:
        rp.login_by_token('/system/user')
        rp.step(2, '点「新增」打开新增用户对话框')
        rp.page.locator('button', has_text='新增').first.click()
        rp.page.wait_for_selector('.el-dialog:visible', timeout=8000)
        dlg = rp.page.locator('.el-dialog:visible').first
        dlg.locator('.el-form-item', has_text='用户昵称').locator('input').first.fill(un)
        dlg.locator('.el-form-item', has_text='用户名称').locator('input').first.fill(un)
        dlg.locator('.el-form-item', has_text='用户密码').locator('input').first.fill('Aa123456')
        dlg.locator('.el-form-item', has_text='备注').locator('textarea').first.fill('R' * 501)
        rp.shot('A25-06-user-form-remark501.png')
        rp.step(3, '点「确 定」提交（备注 501 字符，界面 textarea 无长度上限）')
        off = rp.log_mark()
        dlg.locator('.el-dialog__footer button', has_text='确').first.click()
        msg = rp.page.locator('.el-message').first
        msg.wait_for(state='visible', timeout=6000)
        rp.page.wait_for_timeout(500)
        rp.shot('A25-07-user-toast-rawdberror.png')
        rp._record('toast', '界面弹出: ' + msg.inner_text().strip()[:200])
        row = one("SELECT user_id FROM sys_user WHERE user_name=%s AND del_flag='0'", (un,))
        print('用户腿 toast=%r 库内行=%s' % (msg.inner_text()[:80], row), flush=True)
    finally:
        rp.close()


only = set(sys.argv[1:])
for tag, fn in (('菜单腿', leg_menu), ('用户腿', leg_user)):
    if only and tag not in only:
        continue
    print('== %s ==' % tag, flush=True)
    try:
        fn()
    except Exception:
        traceback.print_exc()
print('补拍完成', flush=True)
