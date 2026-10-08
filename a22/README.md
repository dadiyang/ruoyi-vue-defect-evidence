
## 修后对照（fix/a22-pwd-length-align@b6626c5，换包部署复验）

- a22_postfix_evidence.json：resetPwd 提交 1/30 字符口令均返回「密码长度必须在5到20个字符之间」
  且 sys_user.password 未变；profile/updatePwd 提交 4 字符同样拒绝；
  对照腿 5 字符口令重置成功且可登录（不误伤登录门内口令）。
- 引擎留痕：修前 FAIL（job 2307 实例 46306）、修后 PASS（job 2352 实例 46392）、
  恢复复验 USER-20 回红＋USER-01 守卫绿（job 2353）。
