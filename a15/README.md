# A15 证据（停用角色不失效在线会话；换绑角色同样不刷新旧会话）

复现于 2026-10-08，RuoYi-Vue master @ 6def9d133（本地检出 7b1139f），默认构建默认配置。
前置：admin 现场创建角色（挂参数管理 列表/查询 菜单）与仅挂该角色的用户并登录取令牌。角色与用户用后已清理。
注意：RuoYi 鉴权拒绝走响应体 code（HTTP 状态仍 200），下表 code 均为业务码。

## 腿1：停用角色（UI 操作），旧会话权限不失效

```
基线（角色启用）   GET /system/config/1（旧令牌）                 → code=200
admin 角色列表页把该角色开关置停用（a15_1..3 三帧），
     PUT /system/role/changeStatus {status:1}
停用后             GET /system/config/1（旧令牌）                 → code=200（期望 401/403）
                   GET /system/config/list（旧令牌）              → code=200
```

## 腿2（对照）：编辑角色收回菜单授权，旧会话即时失效——刷新机制在位

```
admin PUT /system/role（menuIds 清空；此路径会触发
     tokenService.refreshPermissionByRoleId 刷新在线会话）
刷新后             GET /system/config/1（旧令牌）                 → code=403（即时生效）
```

同型场景把角色菜单收回 → 旧会话即时 403（回归用例 USER-18 绿证在案）。
即：不是"在线会话无法刷新"，而是 changeStatus 路径没有触发刷新，且刷新也刷不掉停用角色（见源码定位）。

## 腿3：用户换绑角色（旧角色停用中 → 新角色启用且无菜单授权），旧会话同样不刷新，连 /getInfo 自愈也失效

```
换绑前             GET /getInfo（旧令牌）                         → permissions 含 system:config:query
admin PUT /system/user {roleIds:[新角色]}（换绑）
换绑后             GET /system/config/1（旧令牌）                 → code=200（期望 401/403）
                   GET /getInfo（旧令牌）                         → permissions 仍含 system:config:query
自愈尝试后         GET /system/config/1（旧令牌）                 → code=200（仍放行）
```

前端路由守卫依赖 /getInfo 返回的 permissions 自愈——该接口重算时读的仍是会话缓存里的
旧角色快照（user.getRoles()），所以自愈路径也刷不掉，换绑后旧会话权限长期滞留。

## 腿4（对照）：强退即时生效——能力在位

```
admin GET /monitor/online/list 取 tokenId →
     DELETE /monitor/online/{tokenId}（强退）→ 旧令牌 /getInfo code=401（即时失效）
```

服务器错误日志窗口无异常行——各腿请求均被直接放行，无鉴权异常。

源码定位：
- SysRoleController.java `:154-162 changeStatus` 只 updateRoleStatus（改库），不触发任何会话刷新；
  `:129 edit` 调 tokenService.refreshPermissionByRoleId（注释「刷新所有持有该角色的在线用户权限」
  = 上游意图：角色变更即时作用于在线用户）；
- SysUserController.edit（换绑角色路径）同样不调任何 refreshPermission*；
- SysPermissionService.getMenuPermission 按 user.getRoles()（会话缓存的角色对象）过滤
  role.status=='0' 再查菜单权限——缓存对象状态是登录时快照，停用后重算仍按旧状态放行该角色权限，
  所以即使 edit 触发刷新也刷不掉停用角色；换绑场景重算读的还是旧角色列表，自愈也失效；
- 对照（生效通道）：菜单收回型变更走 selectMenuPermsByRoleId 现查 DB → 刷新即生效；
  SysUserOnlineController forceLogout → 即时 401。

新登录侧对照（产品自身语义=停用即失效）：同角色用户停用后重新登录访问同接口 → 403
（回归用例 ROLE-08 绿证在案）。

素材：repro_A15.py（可重放，四腿一次跑完）、a15_evidence.json（结构化证据）、
a15_1_role_list.png / a15_2_confirm_disable.png / a15_3_role_disabled.png（停用操作三帧）。
