
## 修后对照（fix/a9-createTable-statement-whitelist@a5af8eb，换包部署复验）

- a9_postfix_evidence.json：含列名 sleep_time 的合法 DDL 创建成功（物理表建成）；
  混入 drop 的语句被拒且文案指明「仅允许 CREATE TABLE 语句，检测到其他语句类型：SQLDropTableStatement」；
  单独 drop table sys_user 同样被拒且 sys_user 未受损。
- 引擎留痕：修前 FAIL（job 2307 实例 46290）、修后 PASS（job 2344 实例 46380）、
  恢复复验 GEN-04 回红＋GEN-03 守卫绿（job 2345）。
