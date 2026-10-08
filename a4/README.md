
## 修后对照（fix/a4-importtemplate-authz@72d1779，换包部署复验）

- a4_postfix_evidence.json：无 system:user:import 权限用户 POST /system/user/importTemplate →
  body {"code":403,"msg":"没有权限，请联系管理员授权"}（RuoYi 鉴权拒绝走 http=200+body code=403）；
  admin 同调用仍 200 返回 3904 字节 xlsx 模板（导入对话框模板下载不受影响）。
- 引擎留痕：修前 FAIL（job 2307 实例 46296）、修后 PASS（job 2336 实例 46362，钉桩脚本 v3
  修正断言口径后）、恢复复验 MENU-02 回红＋MENU-01 守卫绿（job 2337）。
