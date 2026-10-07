# A15 证据（接口面缺陷，无界面帧）

复现于 2026-10-08，RuoYi-Vue master @ 6def9d133（本地检出 7b1139f），默认构建默认配置。
前置：admin 现场创建角色（挂参数管理 列表/查询 菜单）与仅挂该角色的用户并登录取令牌。角色与用户用后已清理。
注意：RuoYi 鉴权拒绝走响应体 code（HTTP 状态仍 200），下表 code 均为业务码。

```
基线（角色启用）   GET /system/config/1（旧令牌）                 → code=200
admin PUT /system/role/changeStatus {status:1}（停用角色）
停用后             GET /system/config/1（旧令牌）                 → code=200（期望 401/403）
admin PUT /system/role（菜单不变；此路径会触发
     tokenService.refreshPermissionByRoleId 刷新在线会话）
刷新后             GET /system/config/1（旧令牌）                 → code=200（期望 401/403）
对照腿A（撤销生效的通道）：同型场景把角色菜单收回（走 DB 重查菜单）
                   → 旧会话即时 code=403（回归用例 USER-18 绿证在案）
对照腿B（能力在位）：admin GET /monitor/online/list 取 tokenId →
                   DELETE /monitor/online/{tokenId}（强退）→ 旧令牌 code=401（即时失效）
```

服务器错误日志窗口无异常行——各腿请求均被直接放行，无鉴权异常。

源码定位：
- SysRoleController.java `:154-162 changeStatus` 只 updateRoleStatus（改库），不触发任何会话刷新；
  `:129 edit` 调 tokenService.refreshPermissionByRoleId（注释「刷新所有持有该角色的在线用户权限」
  = 上游意图：角色变更即时作用于在线用户）；
- SysPermissionService.getMenuPermission 按 user.getRoles()（会话缓存的角色对象）过滤
  role.status=='0' 再查菜单权限——缓存对象状态是登录时快照，停用后重算仍按旧状态放行该角色权限，
  所以即使 edit 触发刷新也刷不掉停用角色（本次 step5 实测 200 即此因）；
- 对照（生效通道）：菜单收回型变更走 selectMenuPermsByRoleId 现查 DB → 刷新即生效；
  SysUserOnlineController forceLogout → 即时 401。

新登录侧对照（产品自身语义=停用即失效）：同角色用户停用后重新登录访问同接口 → 403
（回归用例 ROLE-08 绿证在案）。

素材：repro_A15.py（可重放）、a15_evidence.json（四腿结构化证据）。
