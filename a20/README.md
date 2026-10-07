# A20 证据（roleMenuTreeselect 无鉴权注解：零权限登录用户可读任意角色的完整菜单授权结构）

复现于 2026-10-08，RuoYi-Vue master @ 6def9d133（本地检出 7b1139f），默认构建默认配置。
后端 8080。测试菜单/角色/用户现场创建、用后清理（残留 0 已实证，软删口径 del_flag）。

## 前置：一个"零权限"用户

admin 现场创建：两条新菜单（id 见 a20_evidence.json seed.menu_ids）、目标角色（挂这两条菜单）、
**不挂任何菜单的角色**及其用户。该用户 `GET /getInfo` → permissions=[]（一条权限都没有）。

## 复现步骤与实测（a20_evidence.json）

```
1) 低权用户 GET /system/menu/roleMenuTreeselect/{目标角色id}
   → code=200，checkedKeys=[两条现造菜单 id]（恰为目标角色被授权的集合）
   同一响应里调用者可见的菜单树 = 0 条（"过滤"只做了展示树，没做授权集）
2) 低权用户 GET /system/menu/roleMenuTreeselect/2（种子「普通角色」）
   → code=200，checkedKeys 68 条（该角色全部功能授权面）
3) 低权用户 GET /system/menu/roleMenuTreeselect/1 → code=200（种子超管角色无菜单行，0 条）
4) 对照腿（同令牌）：
   GET /system/role/{目标角色id} → code=403（system:role:query 在位）
   GET /system/role/list         → code=403
   GET /system/menu/list         → code=403
   GET /system/menu/treeselect   → 200（返回值按调用者过滤，无泄露——对照"有意开放且已过滤"型）
```

## 代码定位

```
SysMenuController.java
  :71-79  roleMenuTreeselect —— 无 @PreAuthorize ——
          menus = selectMenuList(getUserId())            // 按调用者过滤（这半有防线）
          checkedKeys = selectMenuListByRoleId(roleId)   // 目标角色授权集，不过滤（这半敞开）

对照（同数据域均有防线）：
  SysRoleController :78-80  GET /{roleId}  @PreAuthorize system:role:query
  SysRoleController :56-58  GET /list      @PreAuthorize system:role:list
  SysMenuController :35-37  GET /list      @PreAuthorize system:menu:list
权限位 system:role:query 在种子菜单(1007 角色查询)存在——注解缺失是遗漏而非"无权限位可挂"。
```

## 为什么这是缺陷

- 任何登录用户（含零权限：自助注册/共享工号类账号）可枚举任意角色的功能授权面；
  菜单 id 在开源种子中全局固定（1..108+），id 集合可直接还原为"这个角色能用什么功能"；
- 定向提权侦察价值；
- 界面入口（角色列表→分配权限）本就由 system:role:list/edit 把关——端点敞开是遗漏，
  补注解不影响正常使用（与 A4 importTemplate 同型）。

## 复现脚本

`repro_A20.py`（接口腿+对照腿+自清理，输出 a20_evidence.json）。
