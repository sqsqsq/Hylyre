# Fixture — JSON 步骤（做法 A，无运行态 VLM）

用于说明「测试步骤」列可含 `action` / `touch` / `input` / `swipe` / `scroll` 等单行 JSON；可配合 `hylyre run` 真机执行（需 `hylyre[device]` + hdc）。

## 测试用例清单

| 用例编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 关联 AC |
| --- | --- | --- | --- | --- | --- | --- |
| TC-JSON-01 | 登录与输入 | 已安装 | {"action":{"type":"touch","by_text":"登录"}};{"input":{"text":"demo_user","by_id":"username","by_text":null}} | 登录成功（未配 VLM 时不自动校验） | P0 | AC-J-01 |
