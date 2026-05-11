# Hylyre 工程进度

## 2026-05-11 · P0.7 完成（本机 pip / pytest / hylyre）

- **Python**：已通过 `winget install --id Python.Python.3.12 -e` 安装 **3.12.10**（路径示例：`%LocalAppData%\Programs\Python\Python312\python.exe`）。**建议**将以下目录加入用户 PATH，便于直接敲 `python`、`pip`、`hylyre`、`pytest`：
  - `%LocalAppData%\Programs\Python\Python312\`
  - `%LocalAppData%\Programs\Python\Python312\Scripts\`
- **安装与验证**（在仓库根 `e:\1.code\Hylyre`）：
  - `python -m pip install -e ".[dev]"` ✅
  - `python -m hylyre doctor` ✅（已修复：`doctor` 子命令与 `doctor` 模块同名导致的 `AttributeError`，改为 `import doctor as doctor_cmd`）
  - `python -m pytest` ✅ **15 passed**
- **`hylyre doctor` 当前环境**：Python / Node / npm / hdc ✅；**mitmproxy** 未在 PATH（预期 P2 前可选；Lyrebird 需要时安装）。
- **OpenSpec**：`openspec/changes/add-mvp-skeleton/tasks.md` 中 **8.8** 项已含 git commit 勾选（见仓库提交记录）。

### P0 总体状态

| 阶段 | 状态 |
|------|------|
| P0.1–P0.6 | 已完成（见下文归档表） |
| P0.7 | **已完成** |

---

## 2026-05-11 · P1 真机烟测（add-driver-hypium 任务 13）

- **环境**：`python -m pip install -e ".[device]"`；USB 连接真机，`hdc list targets` 可见设备。
- **命令**：
  - `python -m hylyre device list` ✅
  - `python -m hylyre ai tap --device-sn <SN> --x 100 --y 150` ✅（Hypium 自动推 agent / 启 uitest daemon，`touch` 正常返回）
- **仓库**：`.gitignore` 增加 `reports/`（Hypium 默认报告目录，避免误提交）。

---

## 2026-05-11 · P0 构建进展（归档表）

| Todo | 说明 |
|------|------|
| **P0.1 环境前置** | Node v22.22.0、npm 11.11.0；winget 安装 Python 3.12 后本机可跑全流程 ✅ |
| **P0.2 工程脚手架** | `pyproject.toml`、`hylyre/`、CLI、`doctor` ✅ |
| **P0.3 自测试基础设施** | `tests/`、`contracts/`、GitHub Actions ✅ |
| **P0.4 OpenSpec** | `openspec init --tools cursor,codex,claude` ✅ |
| **P0.5 宪章 + change** | `openspec/project.md`、`add-mvp-skeleton` 全套 spec delta ✅ |
| **P0.6 文档** | `README.md`、本文件 ✅ |

### 下一步

- 主目标 **P3**（`HylyreAgent` + Midscene 风格 `ai_*`）；证书 hdc 自动化跟进 **`openspec/changes/add-cert-bootstrap/tasks.md`**。

---

## 2026-05-11 · P2 Lyrebird 与证书分工（闭环）

- **代码交付**：`MockControllerBase` / `LyrebirdController` / `hylyre mock start|stop|status|activate|deactivate|capture|cert`；CI 内 **respx**，不强依赖真 Lyrebird 进程。
- **OpenSpec**：
  - `add-driver-lyrebird`：`tasks.md` 中 **13、14** 已勾选闭环说明（**13** → 独立 change **`add-cert-bootstrap`**；**14** → CLI/测已覆盖，真进程依赖本机安装）。
  - **`add-cert-bootstrap`**：`openspec/changes/add-cert-bootstrap/` 已创建并通过 `openspec validate`（hdc + CA 安装自动化在后续 tasks 实现）。
- **本机真进程烟测（可选）**：在仓库根执行  
  `python -m pip install -e ".[mock]"` → `python -m hylyre mock start --mock-port 9090 --data <mock数据目录>` → `python -m hylyre mock status` → `python -m hylyre mock stop`。  
  **Windows 注意**：`lyrebird` 依赖链可能需编译 `netifaces`，若 pip 报需 **Microsoft Visual C++ Build Tools**，先安装 [Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) 或使用已提供 wheel 的环境（如部分 Linux CI 镜像）。

---

- **`add-mvp-skeleton`** → `openspec/changes/archive/2026-05-11-add-mvp-skeleton/`；稳态能力写入 `openspec/specs/*`。
- **`add-driver-hypium`** → `openspec/changes/archive/2026-05-11-add-driver-hypium/`；`driver-hypium` 等规范合并至主 specs。

---
