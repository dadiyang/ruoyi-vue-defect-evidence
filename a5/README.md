
## 修后对照（fix/a5-job-whitelist-bean-exists@99e3804，换包部署复验）

- a5_postfix_evidence.json：不存在 bean 目标（noSuchBean.foo()）新增返回业务文案
  「新增任务'…'失败，目标字符串不在白名单内」，sys-error.log 零新增异常行；
  合法目标（ryTask.ryParams('ry')）新增仍 200；非白名单 FQCN 拒绝文案不变。
- 引擎留痕：修前 FAIL（job 2307 实例 46291）、修后 PASS（job 2338 实例 46365）、
  恢复复验 JOB-04 回红＋JOB-01 守卫绿（job 2339）。
