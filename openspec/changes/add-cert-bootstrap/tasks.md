# Tasks: add-cert-bootstrap

## 1. 规格与契约

- [ ] 1. 在 `openspec/specs/` 下归档前，本 change 的 `specs/*/spec.md` delta 保持与 `mitm_trust_instructions` / CLI 行为一致

## 2. 实现

- [ ] 2. `cert_bootstrap.py`：从「纯文本」扩展为「命令构建 + 可选 `subprocess` 执行」分层（便于单测 mock）
- [ ] 3. 新 CLI 子命令（命名待与 `mock cert` 统一）：例如 `hylyre mock push-ca --ca ... --serial ...`
- [ ] 4. `hylyre doctor` 一行提示：未检测到 CA / hdc 时的修复链接

## 3. 自测

- [ ] 5. L1：`hdc` 命令行拼装与错误分支单测（不调用真 hdc）
- [ ] 6. （可选）真机：成功 push + 手工安装后浏览器/应用可走代理

## 4. 收口

- [ ] 7. `openspec validate add-cert-bootstrap` 通过后，再 `archive` 合并主 spec
- [ ] 8. 在 `docs/progress.md` 记一条证书自动化首版结论
