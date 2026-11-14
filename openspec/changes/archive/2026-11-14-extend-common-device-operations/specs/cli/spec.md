## ADDED Requirements

### Requirement: CLI coverage of extended operations
CLI SHALL 提供 design.md 清单的原子入口并支持步骤文件/计划/session；touch 沿用 run tap，复杂参数使用 JSON 输入，错误遵循既有拒绝协议。

#### Scenario: Equivalent invocation
- **WHEN** 同一 drag 参数通过原子 CLI 与 --steps-file 执行
- **THEN** 调用同一公共逻辑并给出一致事实和状态
