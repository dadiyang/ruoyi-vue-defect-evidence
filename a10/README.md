# A10 证据（接口面缺陷，无界面帧）

复现于 2026-10-08，RuoYi-Vue master @ 13db1fce。前置：导入 3 列表 t_rgen_a10probe（table_id=100）。

```
GET /tool/gen/column/100                      → HTTP 200 {"total":0,"rows":[],"code":0}
GET /tool/gen/100                             → HTTP 200 code=200 data.rows=3 条（id、name、del_flag）
GET /tool/gen/column/100?tableId=100          → HTTP 200 {"total":3,"rows":[3 条],"code":0}

SELECT column_name FROM gen_table_column WHERE table_id=100 → id、name、del_flag（3 行）

GET /v3/api-docs →
"/tool/gen/column/{tableId}": { "get": { "parameters": [
  {"name":"tableId","in":"query","required":true,"schema":{"type":"integer","format":"int64"}} ] } }
```

源码定位：GenController.java:100-108 `columnList(Long tableId)` 缺 @PathVariable（对照 :71 getInfo 的正确写法）。
