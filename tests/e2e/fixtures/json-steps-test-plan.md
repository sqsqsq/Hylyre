# Fixture — JSON 步骤（做法 A，无运行态 VLM）

用于说明「测试步骤」列可含 planned JSON 根键；完整列表见 **`docs/agent-plan-a.md`** §2.1。

**根键（任选其一）**：`action` / `touch` / `input` / `swipe` / `scroll` / **`back`** / **`home`** / **`stop_app`** / **`clear_app`** / **`wait`** / **`wait_for`** / **`wait_gone`** / **`wait_idle`** / **`assert_toast`** / **`start_app`**

可配合 `hylyre run --plan` 真机执行（需 `hylyre[device]` + hdc）。离线烟测加 **`--use-fakes`**（桩模式不逐步执行 Tier A，仅验证 plan 解析时可另写 unit test）。

## 测试用例清单

| 用例编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 关联 AC |
| --- | --- | --- | --- | --- | --- | --- |
| TC-JSON-01 | 登录与输入 | 已安装 | {"action":{"type":"touch","by_text":"登录"}};{"input":{"text":"demo_user","by_id":"username","by_text":null}} | 登录成功（未配 VLM 时不自动校验） | P0 | AC-J-01 |
| TC-JSON-02 | Nav 返回示例 | 已在子页 | {"back":{}};{"touch":{"by_text":"首页"}} | 回到 Tab 首页（未配 VLM 时不自动校验） | P0 | AC-J-02 |
