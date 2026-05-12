# Design: add-driver-lyrebird

## Decisions

- **Admin API**：对齐官方文档 `GET/PUT http://{mock}/api/...`（`/status`、`/mock/.../activate`、`/flow` 等）；响_body 含 `code` 字段时非 `1000` 抛 `LyrebirdApiError`。
- **子进程**：`lyrebird -b --mock <port> [--data dir]`；需 `pip install 'hylyre[mock]'`（`importlib` 探测）；不在 **`hylyre` 根导入**时硬依赖 `lyrebird`。
- **抓包导出**：`export_flows` 写 JSON 快照（摘要或拉全量 `/api/flow/{id}`），**不宣称**严格 HAR。
- **证书**：P2 只提供 `mitm_trust_instructions()` 文本；`add-cert-bootstrap` 再谈 `hdc`/系统安装自动化。

## Risks

- Lyrebird 主版本间 API 细微差异：以 HTTP 状态 + `code` 字段防御；真机烟测再校准。
