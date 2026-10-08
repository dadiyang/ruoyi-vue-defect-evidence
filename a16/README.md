# A16 证据（Druid 监控台在业务端口暴露 + 出厂默认凭据 → 全量 SQL 与数据库连接信息泄露）

复现于 2026-10-08，RuoYi-Vue master @ 6def9d133（本地检出 7b1139f），默认构建默认配置，
应用端口 8080（上游默认）。无需任何应用账号。

## 复现步骤（curl 即可）

```
1) GET  /druid/index.html            → 302 → /druid/login.html（登录页直接可达）
2) POST /druid/submitLogin
       loginUsername=ruoyi&loginPassword=123456   → "success"
   （凭据即 application-druid.yml:50-51 随源码发布的默认值；
     注意参数名是 loginUsername/loginPassword，不是 username/password）
3) GET  /druid/sql.json              → 253 条 SQL 语句全文（324,743 字节）
   GET  /druid/datasource.json      → JDBC 连接串（内网主机/端口/库名）
   GET  /druid/weburi.json          → 全站接口访问清单与统计（1000 条 URI）
```

## 实测结果（a16_evidence.json）

| 步骤 | 结果 |
|---|---|
| 未登录访问登录页 | http=200，含登录表单 |
| 默认凭据 submitLogin | body=success |
| sql.json | 253 条 / 324743 字节（含建表/查询语句全文） |
| datasource.json | jdbc:mysql://localhost:3306/ry_vue_baseline?... |
| weburi.json | 1000 条 URI 及调用统计 |

## 界面实拍

- a16_1_druid_login_page.png：未登录直达的 Druid 登录页（业务端口 8080）
- a16_2_druid_sql_monitor.png：默认凭据登录后的 SQL 监控页（应用执行过的全部 SQL 可见）

## 源码定位

- SecurityConfig.java `:106`：`/druid/**` 与 swagger 一并 permitAll（免鉴权放行）；
- application-druid.yml `:43-51`：statViewServlet enabled=true、allow 留空（不限来源 IP）、
  login-username=ruoyi / login-password=123456（随源码发布）；
- druid-spring-boot-starter 1.2.28 ResourceHandler：submitLogin 仅校验上述配置凭据，
  无失败次数限制（可无限重试）。

## 影响边界（实测收窄）

1.2.28 版本 session.json / reset.json / sqlDetail.json 返回“不支持”，
本缺陷面为信息泄露型（SQL 全文、JDBC 连接信息、接口访问统计），
未涉及会话劫持与监控统计篡改。对照：/actuator/**、/v3/api-docs 未登录均被鉴权拦截（防线在位），
仅 /druid/** 因 permitAll+默认凭据三道门全破。

素材：repro_A16.py（可重放）、a16_evidence.json（结构化证据）、界面两帧。

## 修后对照（fix/a16-druid-default-off@6531535，换包部署复验）

- a16_postfix_evidence.json：/druid/login.html、submitLogin（默认凭据）、sql.json 三腿
  均回 code=401（认证失败）——监控台默认关闭且 /druid/** 不再匿名放行。
- 引擎留痕：修前 FAIL（job 2307 实例 46301）、修后 PASS（job 2324 实例 46344）、
  恢复复验 SRV-04 回红＋CONF-10 守卫绿（job 2325）。
