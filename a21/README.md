# A21 证据（公告富文本原样入库 + 前端 v-html：存储型 XSS 在全体登录用户浏览器执行）

复现于 2026-10-08，RuoYi-Vue master @ 6def9d133（本地检出 7b1139f），默认构建默认配置。
后端 8080 / 管理端 18091。测试公告/用户/角色现场创建、用后清理（残留 0 已实证）。

## 攻击者与受害者

- 攻击者：持 `system:notice:add`（公告新增，内容运营类常备权限）；本证据用 admin 演示发布。
- 受害者：**不挂任何菜单的角色**下的用户（`GET /getInfo` → permissions=[]），
  登录管理端首页点铃铛即可中招——铃铛入口 `GET /system/notice/listTop` 登录即可达、无权限要求。

## 复现步骤与实测（a21_evidence.json）

```
1) 发布载荷公告：
   <p>常规富文本</p><img src=x onerror="window.__a21xss='pwned'"><script>…</script>
   DB sys_notice.notice_content 回读 → script 标签与 onerror 属性原样在库
2) GET /system/notice/{id} → noticeContent 原样返回（未净化）
3) 零权限受害者登录 → GET /system/notice/listTop → 看到该公告
4) 界面：首页铃铛弹层 → 点该公告 → 预览弹窗渲染（v-html）
   浏览器求值 window.__a21xss → 'pwned'   ← 注入脚本在受害者浏览器实际执行
   （如实记录：<script> 标签经 innerHTML 插入不执行，window.__a21xss2=null；
     事件属性型 onerror 执行——结论仅基于已实证腿）
5) 清理：公告硬删、用户/角色删除，残留 0
```

## 界面实拍

- `A21_01_victim_bell_popup.png`：零权限受害者铃铛弹层可见载荷公告
- `A21_02_victim_preview.png`：预览弹窗（载荷已渲染进 DOM）

## 代码定位

```
ruoyi-admin/src/main/resources/application.yml :141-145
  xss: enabled: true
       excludes: /system/notice      ← 公告域被显式排除在 XssFilter 之外
SysNoticeController add/edit         ← 对 notice_content 无任何服务端净化
RuoYi-Vue3 src/layout/components/HeaderNotice/DetailView.vue :45
  <div class="notice-content" v-html="detail.noticeContent" />   ← 预览直接 v-html
GET /system/notice/listTop（:89-101 无鉴权注解）← 受害者入口登录即可达（有意设计，见 NOTI-06）
```

## 影响

- 权限升级链：公告新增权限 → 任意登录用户浏览器执行任意 JS → 窃取 localStorage 会话令牌
  → 接管包括超级管理员在内的任意账号；
- 受害者无需任何权限、无需被诱导离开系统：首页铃铛是默认入口，新公告全员可见。

## 复现脚本

`repro_A21.py`（API 双腿 + 受害者 UI 腿 + 自清理，输出 a21_evidence.json 与两帧截图）。
