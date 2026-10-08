# A17 证据（缓存监控删除端点：读权限实授删除能力 + 零审计）

复现于 2026-10-08，RuoYi-Vue master @ 6def9d133（本地检出 7b1139f），默认构建默认配置。
后端 8080 / 管理端 18091。测试角色与用户现场创建、用后清理。

## 前置：一个只有"缓存监控"菜单的用户

admin 创建角色（仅挂 监控>缓存监控 菜单，权限=monitor:cache:list 一条读权限）
与两个用户（攻击者/受害者），绑定该角色并登录。

## 复现步骤与实测（a17_evidence.json）

```
1) 攻击者权限集                       → ["monitor:cache:list"]（仅一条读权限）
2) GET  /monitor/cache/getNames       → 七组缓存全可见
   （login_tokens: sys_config: sys_dict: captcha_codes: repeat_submit:
     rate_limit: pwd_err_cnt:）
   GET  /monitor/cache/getKeys/login_tokens:  → 在线会话键 9 个可见
3) 强退腿：DELETE /monitor/cache/clearCacheName/login_tokens:  → code=200
   受害者旧令牌 GET /getInfo          → code=401（被低权用户强退）
4) 解锁腿：攻击者一次错误登录          → pwd_err_cnt:攻击者 = 1
   DELETE /monitor/cache/clearCacheKey/pwd_err_cnt:攻击者 → code=200
   再查计数                           → null（账号锁定保护被清零，暴力破解窗口重开）
5) 审计腿：等待操作日志异步落库(2.5s) 后查 sys_oper_log
   clearCache 相关行数                → 0
   同窗口对照 admin 新增参数 add()    → 3 行（其余写操作正常落日志）
```

## 界面实拍

a17_1_lowpriv_cache_page.png：低权用户登录后缓存监控页——全部缓存组与清空入口可见
（非仅直调可触发）。

## 源码定位

- CacheController.java `:97-119`：clearCacheName / clearCacheKey / clearCacheAll 三个
  DELETE 端点的 @PreAuthorize 全部只要求 `monitor:cache:list`（与只读查询同一权限）；
  clearCacheKey 直接删除调用者传入的任意键；clearCacheAll = `redisTemplate.keys("*")` 全清；
- 全类无 @Log → 三个删除动作均不进操作日志；
- 对照（平台惯例）：定时任务/参数/字典等写操作均带 @Log(title, businessType)，
  且写操作使用独立权限（如 monitor:job:edit）。

## 影响

- 权限语义错位：名为 list 的只读权限实授删除能力，给运维观察类角色授权即连带
  强退他人与重置账号锁定保护；
- clearCacheName/clearCacheAll 可把全体在线用户踢下线（可用性攻击面）；
- pwd_err_cnt: 可删 → "5 次失败锁 10 分钟" 形同可重置开关；
- 事后零审计，无法追查谁清空了缓存/踢了人。

注：管理员"清空缓存会踢掉在线用户"这一能力本身是已知契约（回归用例 CACHE-06 按此断言绿）；
本缺陷在于该能力被读权限放开且无审计。

素材：repro_A17.py（可重放）、a17_evidence.json（结构化证据）、界面一帧。

## 修后对照（fix/a17-cache-clear-authz@c2f58b3，换包部署复验）

- a17_postfix_evidence.json：读权限用户删除 403；admin 删任意前缀键被白名单拒绝（明确文案）；
  admin 删合法前缀键 200；sys_oper_log 出现 clearCache 方法行（审计在案）。
- 引擎留痕：修前 FAIL（job 2307 实例 46284）、修后 PASS（job 2326 实例 46348，
  同 job CACHE-06 守卫绿）、恢复复验 CACHE-09 回红＋CACHE-06 绿（job 2327）。
