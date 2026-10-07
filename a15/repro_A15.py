#!/usr/bin/env python3
"""A15 复现：停用角色不刷新在线会话——被停用角色的用户仍可行使其权限。

上游意图证据（源码现取 RuoYi-Vue master @ 本机部署 jar）：
- SysRoleController.edit(:129)：修改角色后调 tokenService.refreshPermissionByRoleId，
  注释「刷新所有持有该角色的在线用户权限」= 角色变更应即时作用于在线用户；
- SysRoleController.changeStatus(:154-162)：停用角色不调任何会话刷新；
- 权限装载 SQL selectMenuPermsByUserId 按 r.status='0' 过滤停用角色
  （SysMenuMapper.xml；ROLE-08 已实证新登录侧生效）——即"停用=权限失效"是产品自身契约。

复现步骤（全部走接口，账号现造现清）：
1) 造角色（参数管理 list+query 菜单）+ 挂该角色的用户，用户登录取令牌；
2) 旧会话 GET /system/config/1 → 200（前置）；
3) admin PUT /system/role/changeStatus status=1（停用角色）；
4) 旧会话直接 GET /system/config/1（不重登、不经 /getInfo）→ 实际仍 200 = 缺陷本体；
5) 对照腿A：PUT /system/role（菜单不变、status=1，触发 edit 的 refreshPermissionByRoleId）
   → 旧会话再调 → 实际仍 200：刷新虽执行，但 SysPermissionService.getMenuPermission
   按会话缓存的 user.getRoles() 重算（缓存 role.status 仍是停用前 '0'），
   停用角色权限原样写回——停用对在线会话完全无效；
   （菜单收回型撤销走 DB 查菜单，故即时生效 403——引擎 USER-18 绿证在案。）
6) 对照腿B：强退该会话 → 401（撤销类操作里强退是生效的）。

引擎钉桩：ROLE-11（run=190/job=2275 首跑即红）。
"""
import sys

sys.path.insert(0, "/home/irons/dev/ruoyi-regression")
import api

import time
TS = time.strftime('%H%M%S')
UN = f"a15_probe_{TS}"


def main():
    at = api.admin_token()
    rn = f"a15_role_{TS}"
    h, r = api.post("/system/role", token=at, body={
        "roleName": rn, "roleKey": f"a15{TS}", "roleSort": 9, "status": "0",
        "deptCheckStrictly": True, "menuCheckStrictly": True, "menuIds": [1, 106, 1030]})
    assert r.get("code") == 200, r
    rid = api.db("SELECT role_id FROM sys_role WHERE role_name=%s AND del_flag='0'", (rn,))[0]["role_id"]
    h, r = api.post("/system/user", token=at, body={
        "userName": UN, "nickName": "A15探针", "password": "Test12345",
        "deptId": 103, "roleIds": [rid], "status": "0"})
    assert r.get("code") == 200, r
    uid = api.db("SELECT user_id FROM sys_user WHERE user_name=%s", (UN,))[0]["user_id"]

    ut = api.login(UN, "Test12345")
    assert isinstance(ut, str), ut
    evidence = {}
    try:
        _run(at, rid, ut, evidence)
    finally:
        # 清理（finally：中途断言失败也不留残留）
        api.put("/system/role/changeStatus", token=at, body={"roleId": rid, "status": "0"})
        api.delete("/system/user/%d" % uid, token=at)
        api.delete("/system/role/%d" % rid, token=at)
    return evidence


def _run(at, rid, ut, evidence):
    h, r = api.get("/system/config/1", token=ut)
    evidence["step2_before_disable"] = r.get("code")

    h, r = api.put("/system/role/changeStatus", token=at, body={"roleId": rid, "status": "1"})
    assert r.get("code") == 200, r
    h, r = api.get("/system/config/1", token=ut)
    evidence["step4_after_disable_direct"] = r.get("code")  # 期望应 403，实际 200=缺陷

    # 对照腿A：edit 路径（菜单不变）触发 refreshPermissionByRoleId
    row = api.db("SELECT role_name,role_key,role_sort,data_scope,status FROM sys_role WHERE role_id=%s", (rid,))[0]
    h, r = api.put("/system/role", token=at, body={
        "roleId": rid, "roleName": row["role_name"], "roleKey": row["role_key"],
        "roleSort": row["role_sort"], "dataScope": row["data_scope"], "status": "1",
        "menuIds": [1, 106, 1030], "deptCheckStrictly": True, "menuCheckStrictly": True})
    assert r.get("code") == 200, r
    h, r = api.get("/system/config/1", token=ut)
    evidence["step5_after_edit_refresh"] = r.get("code")  # 实际仍 200：刷新按缓存 role.status 重算，刷不掉

    # 对照腿B：强退
    h, r = api.get("/monitor/online/list", token=at)
    tid = next((it["tokenId"] for it in r.get("rows", []) if it.get("userName") == UN), None)
    if tid:
        api.delete("/monitor/online/%s" % tid, token=at)
    h, g = api.get("/getInfo", token=ut)
    evidence["step6_after_forcelogout"] = g.get("code")  # 401

    import json
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
