# Tasks: add-cert-bootstrap

## 1. 规格与契约

- [x] 1. 在 `openspec/specs/` 下归档前，本 change 的 `specs/*/spec.md` delta 保持与 `mitm_trust_instructions` / CLI 行为一致（稳态见 `openspec/specs/cert-bootstrap/spec.md`）

## 2. 实现

- [x] 2. `cert_bootstrap.py`：从「纯文本」扩展为「解析 CA 路径 + `hdc` push」分层（单测 mock `hdc_cli.file_send`）
- [x] 3. 新 CLI：`hylyre mock push-ca`（`--ca-cert` / `--serial` / `--remote`）
- [x] 4. `hylyre doctor`：`mitmproxy CA (PEM)` 行（mitmproxy 在 PATH 时缺失 CA 给指引）

## 3. 自测

- [x] 5. L1：`hdc file send` 拼装与错误分支单测（不调用真 hdc）
- [ ] 6. （可选）真机：成功 push + 手工安装后浏览器/应用可走代理

## 4. 收口

- [x] 7. 稳态 spec 已写入 `openspec/specs/cert-bootstrap/spec.md`（change 目录可后续 `/opsx:archive` Formal 归档）
- [x] 8. 在 `docs/progress.md` 记一条证书自动化首版结论

