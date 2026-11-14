# Fixed read-only Shell plan acceptance

## 测试用例清单

| 用例编号 | 用例名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 关联 AC |
| --- | --- | --- | --- | --- | --- | --- |
| SHELL-PLAN-1 | Shell JSON string boundary | Selected acceptance device | {"shell":{"command":"printf '%s\\n' '中文;分号；与 空格' 'quote\"single'\n"}}；{"shell":{"command":"printf 'second\\n'"}} | | P2 | AC-COMMON-SHELL |
