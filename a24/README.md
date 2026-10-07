# A24 证据（字典数据新增无类型+值查重：同类型同字典值可重复创建，消费端同值多标签并存）

复现于 2026-10-08，RuoYi-Vue master @ 13db1fc，默认构建默认配置，后端 8080。
测试字典类型/数据现场创建、用后清理（残留 0 已实证）。

## 复现（repro_A24.py，一次跑完全部取证）

1. 建字典类型 dict_pdu1008035508；
2. POST /system/dict/data 值 dupval 标签A → 200；再 POST 值 dupval 标签B → 200（应被拒）；
3. 库查两行（dict_code 206/207）；消费接口 GET /system/dict/data/type/{type} 返回同值两标签；
   Redis 缓存 sys_dict:{type} 同步含两条；
4. 清理后残留 0。

## 三层无防线（代码定位）

- 控制器 SysDictDataController.java:89-95 add 无查重；
- 服务层全仓无 checkDictDataUnique（类型侧 checkDictTypeUnique 存在，对照）；
- 库 sql/ry_20260417.sql:496 仅主键，无 (dict_type,dict_value) 唯一索引；
- 标签反查 DictUtils.java:99 HashMap put 覆盖→只取最后一条。

## 引擎留痕

TCMS 项目 ruoyi-vue 轮12 job 2311：钉桩 DICT-11 首跑即红（断言：同类型同值第二次新增应被拒，实际 200）。

## 界面实拍

a24-01-dictdata-dup-rows.png：管理端 字典管理→本轮类型行「列表」→字典数据列表，
同键值 dupval 两行并存（标签A/标签B，类型 dict_a241008035842，2026-10-08 03:58，用后清理残留 0）。
复现脚本 repro_A24.py（造数走 API、界面呈现现象并截图）。
