
## 修后对照（fix/a1-datascope-comment-include-5@fc56b57，对在役库应用修正注释复验）

- a1_postfix_evidence.json：ALTER 后 SHOW FULL COLUMNS 读回注释含「5：仅本人数据权限」，
  列类型 char(1)/默认值 1 不变；恢复基线注释后读回缺 5（换库无残留）。
- 引擎留痕：修前 FAIL（job 2346 实例 46383，新钉桩 ROLE-15 首跑）、修后 PASS（job 2347 实例 46384）、
  恢复复验 ROLE-15 回红＋ROLE-01 守卫绿（job 2348）。
