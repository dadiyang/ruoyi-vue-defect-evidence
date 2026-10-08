# A25 素材：表单超长输入直接返回数据库报错原文

界面实拍（管理端 :18091，无头 Chromium，令牌注入会话）：

- A25-01-landed.png：定时任务列表页（admin）
- A25-02-form-65chars.png：新增任务对话框，任务名称填 65 字符（输入框无 maxlength）
- A25-03-toast-rawdberror.png：决定性帧——点「确定」后界面顶部提示条整段显示 job_name 列数据库异常原文
- A25-04-menu-form-routename51.png：新增菜单对话框，路由名称填 51 字符（无 maxlength）
- A25-05-menu-toast-rawdberror.png：决定性帧——route_name 列异常原文提示条
- A25-06-user-form-remark501.png：新增用户对话框，备注填 501 字符（textarea 无 maxlength）
- A25-07-user-toast-rawdberror.png：决定性帧——remark 列异常原文提示条

复现脚本：repro_A25_job_leg.py（任务腿）、repro_A25_menu_user_legs.py（菜单/用户腿）。
部门 leader 腿为接口直调（界面输入框 maxlength=20 挡得住），响应原文见缺陷报告。

## 修后对照（fix/a25-field-size-validation@9ce17a9，换包部署复验）

- a25_postfix_evidence.json：超长输入返回中文长度文案（如「任务名称不能超过64个字符」）；
  限长内保存不受影响（64 字符任务名、500 字符备注均 200）。
- 引擎留痕：修前 FAIL（job 2376 实例）、修后 PASS（job 2378）、恢复复验回红（job 2379）。
