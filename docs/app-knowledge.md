# App 知识持久化（Hylyre）

Hylyre 提供 **app 级页面快照**、**selector 索引**、**裁剪 dump**、**实时 flat find** 与 **结构指纹** 原语；schema 由 Hylyre 定义（`hylyre-app-page-v1` / `hylyre-app-index-v1`），Framework 可与本仓库共享同一 JSON。

详细设计动机见仓库内「App Knowledge Persistence Layer」计划（`.cursor/plans/`，勿编辑该文件）。

## 存储路径解析链

写入（首个可写目录）优先级：

1. CLI **`--store-dir`**
2. 环境变量 **`HYLYRE_APP_STORE_DIR`**
3. **`<cwd>/.hylyre/apps`**

读取合并顺序（同名快照以先找到的为准）：

1. **`--store-dir`**（若传入）
2. **`HYLYRE_APP_STORE_DIR`**
3. **`<cwd>/.hylyre/apps`**
4. **`~/.hylyre/apps`**（仅读取兜底）

API：`hylyre.app_store.paths.resolve_read_dirs` / `resolve_write_dir`。

### 三种调用方

| 场景 | 推荐 |
|------|------|
| Cursor MCP（cwd = 仓库根） | 不传 `store_dir`，读写默认落在 `./.hylyre/apps` |
| Framework 子进程 | 显式 **`--store-dir ./cache/apps`**（或 MCP `store_dir` 参数） |
| CI | 设置 **`HYLYRE_APP_STORE_DIR`** 指向流水线缓存目录 |

## CLI 速查

- **裁剪 dump**：`hylyre dump-ui ...`（`--filter-text` / `--full` / `--summary` 等，见 `hylyre dump-ui --help`）
- **当前屏扁平查找**：`hylyre find --session FILE --by-text "文案"`  
  返回 JSON 对象：`hits`（节点数组）、`_hylyre_hints`（与 `dump-ui` 根级相同的滚动提示，可能为空对象）、`limit`、`truncated`。
- **快照**：`hylyre app page save|load|list|diff|delete`（见 `--help`）
- **跨已入库页查 selector**：`hylyre app find --bundle com.example.app --by-text "文案"`
- **指纹**：`hylyre app fingerprint --session FILE`（或 `--from-dump tree.json`）

## MCP 工具（与 CLI 对等）

- **`hylyre_find`**：同上，返回 **`hits` + `_hylyre_hints`**，无需单独 `dump-ui` 也能看到 `scrollable_containers` / `likely_more_content_*`。
- **`hylyre_app_page_save`** / **`hylyre_app_page_load`** / **`hylyre_app_page_list`** / **`hylyre_app_page_diff`** / **`hylyre_app_page_delete`**
- **`hylyre_app_find`**：扫合并后的 `index.json`
- **`hylyre_app_fingerprint`**

与 **`hylyre_collect_list`** 相同：**`session_id`、`session_path`、`device_sn` 至多选一个**。

## Schema 摘录

页面快照 `<store>/<bundle>/pages/<name>.json` 含：`tree`（完整 augment 后的 dump-ui 负载，含 `_hylyre_hints`）、`key_elements`、`fingerprint`（可选）、`actions`（预留数组）。

索引 `<store>/<bundle>/index.json` 的 `elements` 将 `by_id` / `by_key` / 文本哈希映射到出现过该元素的 **page 列表**。

用 **`hylyre app page load`** 读出的快照中，滚动提示在 **`snap["tree"]["_hylyre_hints"]`**（`tree` 存的是整份 augment 后的 dump-ui 负载）。

## Knowledge-first 循环

见 **[agent-loop.md](./agent-loop.md)**「Knowledge-first loop」：先 **`app page load`** + **`app find`**（或 MCP 等价），避免重复整树 dump；首次探索完成后 **`app page save`** 更新缓存。
