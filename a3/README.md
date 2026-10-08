
## 修后对照（fix/a3-dept-cycle-check@5c1ec06，换包部署复验）

- a3_postfix_evidence.json：把部门移到自身子孙下返回「修改部门'…'失败，上级部门不能是其子孙」
  且 P/C/G 的 ancestors 均未被污染；对照腿：合法移动（挂到另一棵子树）仍 200 且
  C/G 的 ancestors 正确刷新。
- 引擎留痕：修前 FAIL（job 2307 实例 DEPT-04 #46286 / DEPT-09 #46287）、
  修后 PASS（job 2354，同 job DEPT-01 守卫绿）、恢复复验双钉回红＋守卫绿（job 2355）。
