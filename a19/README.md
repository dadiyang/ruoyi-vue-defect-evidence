# A19 证据（菜单编辑：上级选择器含自身与子孙 + 接口无环检测 → 正常界面操作即可成环）

复现于 2026-10-08，RuoYi-Vue master @ 6def9d133（本地检出 7b1139f），默认构建默认配置。
后端 8080 / 管理端 18091。测试菜单现场创建、用后清理（残留 0 已实证）。

## 前置：三级菜单链

admin 经接口现造 a19Parent > a19M3 > a19M31（menuId 见 a19_evidence.json seed.ids），
`GET /system/menu/treeselect` 三节点均可见（前置成立）。

## 复现步骤与实测（a19_evidence.json）

```
1) 界面：菜单管理页 → a19M3 行「修改」→ 点开「上级菜单」树选择器
   可选项（展开后）                    → a19Parent、a19M3（自身）、a19M31（其子）
   self_selectable / descendant_selectable → true / true
2) 把上级选成 a19M31（它自己的子菜单）→ 保存
   PUT /system/menu                   → http=200 {"code":200,"msg":"操作成功"}
3) 保存后菜单管理页树表 a19 行数       → 3 → 1（a19M3、a19M31 整条子树消失）
4) 互证：GET /system/menu/treeselect  → 已无 a19M3/a19M31
   GET /system/menu/list（平表）      → 仍 3 行（数据未丢，展示层不可达）
   parent_id 映射                     → a19M3→a19M31、a19M31→a19M3（环成立）
5) 清理：先把 a19M3 上级经接口改回原父（接口只拦"上级是自己"，挂回原父可过），
   再删除三节点                        → 库内 a19 残留 0
```

## 界面实拍

- `A19_01_menu_tree.png`：菜单树基线（a19 三级链可见）
- `A19_02_parent_options.png`：编辑 a19M3 时上级选择器展开——**自身 a19M3 与其子 a19M31 均可点选**
- `A19_03_child_as_parent.png`：已把子菜单 a19M31 选为上级
- `A19_04_after_save_tree.png`：保存提示"操作成功"后，树里 a19M3/a19M31 消失

## 对照（为什么这是缺陷）

- 部门编辑的上级选择走 `GET /system/dept/list/exclude/{deptId}`
  （SysDeptController.excludeChild:53-59），**已剔除自身与全部子孙**；
  菜单编辑的上级选择器数据源是 `listMenu()` 全量（views/system/menu/index.vue:354-358），**不剔除**。
- 后端 SysMenuController.edit(:111-131) 只拦"上级菜单不能选择自己"（:121-123），
  无"新上级属自身子孙"环检测。
- 环成立后 buildMenuTree/handleTree 按 parent_id 构树，环内节点从根不可达：
  菜单管理页、角色授权菜单树（roleMenuTreeselect）、登录路由下发（getRouters）三处同时丢块。

## 与 A3（部门成环）的分野

A3：部门界面已剔除自身与子孙，仅接口直调可触发（api 面，ENHANCE）。
A19：菜单界面本身把非法选项摆到用户面前，**正常界面操作即可触发**（admin 界面面，BUG）。
模块不同（sys_menu vs sys_dept）、防线状态不同、修复位置不同，非重复卡。

## 复现脚本

`repro_A19.py`（Playwright + 接口互证，输出 a19_evidence.json 与四帧截图）。

## 修后对照（后端 fix/a19-menu-cycle-check@da385ca＋前端 fix/a19-menu-tree-exclude@a2cd198，换包部署复验）

- a19-postfix-tree-exclude.png：编辑菜单 M 时「上级菜单」树下拉不再出现 M 自身与其子菜单 MC
  （父 P 仍可选）；API 腿同口径拒绝：「上级菜单不能选择自己或自己的子菜单」。
- 引擎留痕：修前 FAIL（job 2307 实例 46297）、修后 PASS（job 2328 实例 46351）、
  恢复复验 MENU-09 回红＋MENU-01 守卫绿（job 2329）。
