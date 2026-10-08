# A12 证据（接口面缺陷，无界面帧）

复现于 2026-10-08，RuoYi-Vue master @ 6def9d133（本地检出 7b1139f），默认构建默认配置。
前置：admin 现场创建哨兵参数 `cfg.a12probe1008012426 = SECRET-A12-VALUE-7Q`（config_id=273）
与仅 common 角色用户 `u_a12low1008012426`（无任何 system:config 权限）。探针参数与用户用后已清理。

```
低权限 GET /system/config/list                          → body.code=403（无 system:config:list）
低权限 GET /system/config/273                           → body.code=403（无 system:config:query）
低权限 GET /system/config/configKey/cfg.a12probe1008012426
                                                        → code=200 {"msg":"SECRET-A12-VALUE-7Q"} 明文回传
无令牌 GET /system/config/configKey/…                    → body.code=401（登录校验在）
admin   GET /system/config/configKey/…                   → code=200 正常值（对照）
```

服务器日志（sys-error.log）同窗口仅两条 Access Denied，分别对应 list/byid 两条对照腿；
configKey 腿无异常行——放行即直读。

源码定位：SysConfigController.java `:40 list` 与 `:62 getInfo` 均有
`@PreAuthorize("@ss.hasPermi('system:config:…')")`，而 `:72 getConfigKey` 没有——
同控制器内权限注解不对称。

## 修后对照（fix/a12-configkey-authz@a834022，换包部署复验）

- a12_postfix_evidence.json：同一越权腿（无 config 权限用户 GET /system/config/configKey/{key}）
  修复构建下返回 code=403「没有权限，请联系管理员授权」；admin 同调用仍 200＋值明文；
  无令牌仍 401。
- 引擎留痕：修前 FAIL（job 2307 实例 46285）、修后 PASS（job 2316 实例 46330）、
  恢复复验 CONF-08 回红＋CONF-10 守卫绿（job 2317）。
