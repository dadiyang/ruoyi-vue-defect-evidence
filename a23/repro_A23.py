# -*- coding: utf-8 -*-
"""A23 复现：参数管理「新增」表单默认「系统内置=是」，界面创建的参数永久不可删。
契约现取：RuoYi-Vue3 views/system/config/index.vue:225 reset() 默认 configType:"Y"；
SysConfigServiceImpl.deleteConfigByIds(:159) 对 configType='Y' 拦「内置参数【x】不能删除」；
DB 列默认 'N'（sql/ry_20260417.sql:539）——API 直调不带该字段仍为 N 可删，缺陷仅在界面默认值。
判据（修复无关不变量）：用户经界面新建的参数应可删除。"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'exec'))
sys.path.insert(0, str(ROOT / 'exec' / 'master'))
os.environ.setdefault('TCMS_ARTIFACT_DIR', str(ROOT / 'reports' / 'shots-r1'))

from api import admin_token, ck, db, delete, one, post, uniq  # noqa: E402
from test_ui_a import _ui, _btn, _dialog, _confirm_box, _row, _search  # noqa: E402

key = uniq('a23')
rp = _ui('A23', '/system/config')
try:
    rp.step(2, '点「新增」——不触碰「系统内置」单选，直接填三项')
    _btn(rp.page, '新增').click()
    rp.page.wait_for_timeout(800)
    dlg = _dialog(rp.page, '添加')
    dlg.locator('input[placeholder="请输入参数名称"]').first.fill(key)
    dlg.locator('input[placeholder="请输入参数键名"]').first.fill(key)
    dlg.locator('textarea[placeholder="请输入参数键值"]').first.fill('1')
    checked = dlg.locator('.el-radio.is-checked').first.inner_text().strip()
    rp._record('form', '「系统内置」单选默认选中=%r' % checked)
    rp.shot('a23-01-form-default.png')
    _btn(rp.page, '确 定', dlg).click()
    toast = rp.grab_toast()
    ck(toast and '成功' in toast, 'A23 前置：UI 新增应成功，实际 %s' % toast)
    rp.page.wait_for_timeout(3500)  # 等「新增成功」toast 消失，防删除腿抓到旧提示
    row = one("SELECT config_id, config_type FROM sys_config WHERE config_key=%s", (key,))
    ck(row, 'A23 前置：UI 新增后库内应查到')
    ck(row['config_type'] == 'Y',
       'A23 实锤①：界面新建参数落库 config_type=%r（表单默认内置=是），用户创建的参数被标成系统内置' % row['config_type'])
    did = row['config_id']
    rp.step(3, '界面删除该参数——应被「内置参数不能删除」拦下（永久不可删实锤）')
    _search(rp, '请输入参数键名', key)
    r = _row(rp, key)
    r.locator('button', has_text='删除').first.click()
    _confirm_box(rp)
    toast = rp.grab_toast()
    rp.shot('a23-02-delete-blocked.png')
    ck(toast and '不能删除' in toast, 'A23 实锤②：界面删除被拦并弹「内置参数【%s】不能删除」，实际 %s' % (key, toast))
    ck(one("SELECT config_id FROM sys_config WHERE config_id=%s", (did,)),
       'A23 实锤③：被拦后行仍在——界面创建的参数无法经界面/接口删除（仅能改库）')
    rp.step(4, '对照腿：API 直调不带 configType（DB 列默认 N）→ 可正常删除')
    http, r2 = post('/system/config', {'configName': key + '_api', 'configKey': key + '_api',
                                       'configValue': '1', 'remark': 'a23'},
                    token=admin_token(), kind='POST /system/config(对照:不带configType)')
    ck(r2.get('code') == 200, 'A23 对照腿：API 造参数应成功，实际 %s' % r2)
    arow = one("SELECT config_id, config_type FROM sys_config WHERE config_key=%s", (key + '_api',))
    ck(arow['config_type'] == 'N', 'A23 对照腿：API 不带该字段应落 DB 列默认 N，实际 %r' % arow['config_type'])
    http, r3 = delete('/system/config/%s' % arow['config_id'], token=admin_token(), kind='DELETE /system/config(对照)')
    ck(r3.get('code') == 200, 'A23 对照腿：N 参数应可删（防线只保护真内置），实际 %s' % r3)
finally:
    rp.close()
    db("DELETE FROM sys_config WHERE config_key=%s", (key,))  # 探针残留清理（内置标记致接口不可删，走库清）
    print('A23 repro done, key=%s' % key)
