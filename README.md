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

## Lyrebird（HTTP Mock）工具链

使用 `hylyre mock …` 连接本机或远程 **Lyrebird** 前，请先准备依赖（也可用 `python -m hylyre doctor` 做自检）：

1. **Python 包**：`pip install 'hylyre[mock]'`（等同安装 `lyrebird`）。官方说明：<https://github.com/Meituan-Dianping/lyrebird#install>
2. **mitmproxy**：代理链路需要，PATH 中能运行 `mitmproxy` 或 `mitmdump`；安装见 <https://mitmproxy.org/>
3. **Windows**：按 Lyrebird 文档准备 **预编译 OpenSSL**，并配置环境变量 **`LIB`**、**`INCLUDE`** 指向对应目录；若 `pip` 编译 `netifaces` 等失败，需安装 **Microsoft C++ Build Tools**
4. **Docker（可选）**：可用镜像 `overbridge/lyrebird` 跑 Lyrebird，把管理 API 暴露到本机端口后，设置环境变量 **`HYLYRE_LYREBIRD_URL`**（例如 `http://127.0.0.1:9090`），即可在不使用 `hylyre mock start` 子进程的情况下对接
5. **VLM（P3，`hylyre ai action|query|assert`）**：需配置 **`HYLYRE_VLM_ENDPOINT`**（OpenAI 兼容 `…/v1/chat/completions`）、可选 **`HYLYRE_VLM_API_KEY`**、**`HYLYRE_VLM_MODEL`**；未配置时自然语言子命令会报错退出

## 当前阶段

**P0 已完成**（2026-05-11）：可编辑安装、`doctor`、`pytest` 冒烟、OpenSpec `add-mvp-skeleton` 有效。**P1**：`UiDriverBase` + Hypium 驱动与 fake 测试（见 `docs/plan.md`）。

## License

MIT（与上游依赖许可证分别遵守）。
