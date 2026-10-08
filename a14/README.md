# A14 证据（接口面缺陷，无界面帧）

复现于 2026-10-08，RuoYi-Vue master @ 6def9d133（本地检出 7b1139f），默认构建默认配置。
前置：admin 现场创建仅 common 角色用户（有 notice:list 权限）并登录取令牌。用户用后已清理。
注意：RuoYi 鉴权拒绝走响应体 code（HTTP 状态仍 200），下表 code 均为业务码。

```
基线（启用中）    GET /system/notice/list（旧令牌）            → code=200
admin PUT /system/user/changeStatus {status:1}（停用）
停用后            GET /system/notice/list（旧令牌）            → code=200（期望 401）
                  GET /getInfo（旧令牌）                       → code=200（期望 401）
admin PUT /system/user/changeStatus {status:0}（恢复）
admin PUT /system/user/resetPwd（重置密码，新口令可登录已对照）
重置密码后        GET /system/notice/list（旧令牌）            → code=200（期望 401）
admin DELETE /system/user/{id}（删除用户）
删除后            GET /system/notice/list（旧令牌）            → code=200（期望 401）
                  GET /monitor/online/list?userName=…          → 仍含该用户会话 1 条
对照腿（能力在位）：另一现造用户登录 → admin GET /monitor/online/list 取 tokenId →
                  DELETE /monitor/online/{tokenId}（op code=200）→ 旧令牌 code=401（即时失效）
```

服务器错误日志窗口无异常行——三段请求均被直接放行，无鉴权异常。

源码定位：
- SysUserController.java `:210 changeStatus`、`:195 resetPwd`、`:180 remove` 只改库，不清 Redis 会话；
- JwtAuthenticationTokenFilter.java `:34-37` 只认 login_tokens:{uuid} 是否存在，不查用户当前状态；
- TokenService.java `:134-141 verifyToken` 剩余不足 20 分钟自动 `:149 refreshToken` 滑动续期（持续访问则无限期有效）；
- 对照 SysUserOnlineController.java `:75-80` forceLogout → deleteObject(login_tokens:{tokenId}) → 即时 401。

## 修后对照（fix/a14-token-invalidate@8881d06，换包部署复验）

- a14_postfix_evidence.json：同一用户旧令牌——停用后 401、重置密码后 401、删除账号后 401
  （操作前 200 对照）。
- 引擎留痕：修前 FAIL（job 2307 实例 46304）、修后 PASS（job 2320 实例 46336）、
  恢复复验 USER-17 回红＋USER-09 守卫绿（job 2321）。
