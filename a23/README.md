# A23 参数管理新增表单默认「系统内置=是」致界面创建的参数永久不可删

- a23-01-form-default.png：参数管理→新增对话框，「系统内置」单选默认选中「是」（不触碰即中招）
- a23-02-delete-blocked.png：对界面新建参数点删除确认后弹「内置参数【a231008034431】不能删除」，行未消失
- repro_A23.py：复现脚本（UI 新增→库内 config_type='Y' 读回→界面删除被拦→对照腿 API 不带字段落 'N' 可删）

根因：RuoYi-Vue3 src/views/system/config/index.vue:225 reset() 默认 configType:"Y"；
SysConfigServiceImpl.deleteConfigByIds(:159) 对 'Y' 一律拦截。DB 列默认与 API 直调均为 'N'（sql/ry_20260417.sql:539）。
钉桩例 CONF-12（界面新建参数可删性不变量）引擎首跑即红（TCMS job 2308）。

## 修后对照（前端 fix/a23-config-default-not-built-in@bae3b27，换码热更新复验）

- a23-postfix-default-no.png：参数管理「新增」对话框「系统内置」默认选中「否」；
- a23_postfix_evidence.json：新建后库内 config_type='N'、DELETE 返回 200；
  显式 configType='Y' 建的参数仍被「内置参数【x】不能删除」拦截（防线不回归）。
- 引擎留痕：修前 FAIL（job 2309 实例 46308）、修后 PASS（job 2332 实例 46357）、
  恢复复验 CONF-12 回红＋CONF-10 守卫绿（job 2333）。
