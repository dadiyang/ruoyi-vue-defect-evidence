# A26 素材：角色权限字符里的逗号让使用者角色列表多出 admin

界面实拍（管理端 :18091，无头 Chromium，令牌注入会话——账号 a26probe 为挂
「含逗号权限字符」角色的普通用户）：

- A26-01-gen-page-create-btn.png：决定性帧——代码生成页显示仅管理员可见的「+ 创建」按钮
- A26-02-create-denied.png：决定性帧——点击创建提交建表 SQL，右上角弹「当前操作没有权限」（403）

复现脚本：repro_A26.py（含前置造数与清场）。

## 修后对照（fix/a26-rolekey-no-comma@266af71，换包部署复验）

- a26_postfix_evidence.json：含逗号权限字符保存被拒（「权限字符不能包含逗号」）；
  正常权限字符保存不受影响。
- 引擎留痕：修前 FAIL（job 2376；断言整改后基线复跑 job 2380 仍 FAIL）、
  修后 PASS（job 2381）、恢复复验回红（job 2382）。
