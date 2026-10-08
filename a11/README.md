
## 修后对照（fix/a11-username-length-align@fb2511a，换包部署复验）

- a11-postfix-import-rejected.png：同一 25 字符登录名称模板，修复构建下界面导入弹窗明确报错
  「userName: 用户账号长度必须介于2和20之间」；接口腿同口径拒绝（code=500 同文案）。
- 引擎留痕：修前 FAIL（job 2307 实例 46303）、修后 PASS（job 2314 实例 46327）、
  恢复复验 USER-15 回红＋USER-09 守卫绿（job 2315）。
