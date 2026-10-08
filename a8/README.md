
## 修后对照（fix/a8-import-dedup@1ba868c，换包部署复验）

- a8_postfix_evidence.json：首次导入 200；重复导入返回「导入失败，表【…】已导入」且
  gen_table 仍 1 行、gen_table_column 不翻倍；未导入过的表仍正常导入（对照腿）；
  混合批（已导入＋新表）返回「导入成功；已跳过重复导入的表：…」且新表正常入库。
- 引擎留痕：修前 FAIL（job 2307 实例 46289）、修后 PASS（job 2356 实例 46402）、
  恢复复验 GEN-02 回红＋GEN-03 守卫绿（job 2357）。
