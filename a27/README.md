# A27 素材：新建用户已设自定义密码，首次登录仍弹「密码还是初始密码」提示

界面实拍（管理端 :18091，无头 Chromium，令牌注入会话——账号为接口新建、
创建时已设自定义口令 CustomPw@2026x 的用户）：

- A27-01-initpwd-prompt.png：决定性帧——登录进入首页即弹「安全提示：您的密码还是初始密码，请修改密码！」

复现脚本：repro_A27.py（含前置造数与清场）。

## 修后对照（fix/a27-pwd-update-date-on-create@f15e179，换包部署复验）

- a27_postfix_evidence.json：自定义口令新建用户 getInfo isDefaultModifyPwd=false，不再误报。
- 引擎留痕：修前 FAIL（job 2385，真断言；首跑 job 2377 的 FAIL 系用例脚本病不作数）、
  修后 PASS（job 2384）。
