# A13 证据（接口面缺陷，无界面帧）

复现于 2026-10-08，RuoYi-Vue master @ 6def9d133（本地检出 7b1139f），默认构建默认配置。
前置：admin 现场创建仅 common 角色用户（无任何 test 相关权限）并登录取令牌。用户用后已删除。

```
低权限 GET   /test/user/list            → code=200，2 条演示用户，每条含明文 password（值=admin123，与 admin 登录口令同值）
低权限 PUT   /test/user/update          → code=200，userId=2 的 password 改为哨兵 A13-WRITESIDE-SENTINEL
低权限 GET   /test/user/2               → 回读 password=A13-WRITESIDE-SENTINEL（写面真实生效；随后已恢复原值）
无令牌 GET   /test/user/list            → body.code=401（登录校验在；注意 RuoYi 鉴权拒绝走 body.code，HTTP 状态仍 200）
低权限 DELETE /system/user/1            → body.code=403（对照：系统模块同类接口有权限校验）
GET /v3/api-docs                        → 公开 4 条 /test/user/** 路径：
  /test/user/list、/test/user/save、/test/user/update、/test/user/{userId}（GET+DELETE 共 5 个操作）
```

源码定位：TestController.java `:28-29` 类上仅 `@RestController + @RequestMapping("/test/user")`，
五个端点（:39 list、:47 getInfo、:62 save、:74 update、:92 delete）均无 `@PreAuthorize`；
`:117-118` UserEntity.password 字段随列表/查询原样返回（无脱敏）。
对照 SysUserController 各端点均有 `@PreAuthorize("@ss.hasPermi('system:user:…')")`。
SecurityConfig `:102-110` 白名单不含 /test/**——即需登录，但登录后不做任何权限校验。

## 修后对照（fix/a13-testcontroller-authz@515db1e，换包部署复验）

- a13_postfix_evidence.json：低权限用户 GET /test/user/list → code=403；
  admin 列表 200 但响应无 password 值（脱敏）、详情 password=null。
- 引擎留痕：修前 FAIL（job 2307 实例 46302）、修后 PASS（job 2318 实例 46333）、
  恢复复验 TST-01 回红＋CONF-10 守卫绿（job 2319）。
