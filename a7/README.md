
## 修后对照（fix/a7-log-date-range-day-grain@8f878df，换包部署复验）

- a7_postfix_evidence.json：操作日志 [今天,今天] total=1054=库内当日数；
  [昨天,昨天] total=0=库内昨日数（边界不越界）；全时间戳区间同值（对照腿不变）；
  登录日志 [今天,今天] total=263（当日记录命中）。
- 引擎留痕：修前 FAIL（job 2307 实例 LOG-04 #46295 / LGIN-02 #46293 / LGIN-07 #46294）、
  修后 PASS（job 2342 实例 #46373/#46371/#46372）、恢复复验三钉回红＋LOG-01/LGIN-01 守卫绿（job 2343）。
