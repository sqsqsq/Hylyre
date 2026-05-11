# Hylyre

面向鸿蒙（HarmonyOS）真机测试的统一工具：**Hypium**（UI 自动化）+ **Lyrebird**（HTTP/HTTPS Mock），CLI 优先，可选 MCP 薄封装；对外 API 风格参考 [Midscene](https://midscenejs.com/api) 的语义动词。

- **规划（SSOT）**：[docs/plan.md](docs/plan.md)
- **进度**：[docs/progress.md](docs/progress.md)
- **输出契约（SSOT）**：`hylyre/contracts/`（`trace.json` / 测试报告章节与枚举）

与业务仓 [SimulatedWalletForHmos](https://github.com/sqsqsq/SimulatedWalletForHmos) 的 **framework** 为**单向输出**关系：本仓不引用其代码；兼容性别名通过 GitHub Actions `compat-framework.yml` **软提醒**（不阻塞主 CI）。

## 技术栈与规范

- Python ≥3.10，CLI [Typer](https://typer.tiangolo.com/)
- 规约与变更：[OpenSpec](https://openspec.dev/)（`/opsx:propose` 等，见 `.cursor/commands`）
- 参考：[Hypium](https://pypi.org/project/hypium/)，[Lyrebird](https://github.com/Meituan-Dianping/lyrebird)

## 快速开始（需本机 Python 3.10+）

若刚用 winget 安装 Python，可将 `%LocalAppData%\Programs\Python\Python312` 与 `\Scripts` 加入用户 **PATH**，或全程使用：

```bat
"%LocalAppData%\Programs\Python\Python312\python.exe" -m pip install -e ".[dev]"
"%LocalAppData%\Programs\Python\Python312\python.exe" -m hylyre doctor
"%LocalAppData%\Programs\Python\Python312\python.exe" -m pytest
```

全局 OpenSpec CLI（已 npm 安装时 PATH 需含 `%AppData%\npm`）：

```bash
openspec list
```

## 当前阶段

**P0 已完成**（2026-05-11）：可编辑安装、`doctor`、`pytest` 冒烟、OpenSpec `add-mvp-skeleton` 有效。**P1**：`UiDriverBase` + Hypium 驱动与 fake 测试（见 `docs/plan.md`）。

## License

MIT（与上游依赖许可证分别遵守）。
