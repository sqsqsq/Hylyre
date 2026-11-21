# Hylyre 需求｜Windows 后台设备会话启动时不弹终端窗口

**提出方**　AgentMaison 宿主集成方，2026-11-20

**问题版本**　Hylyre 0.6.1，Windows 桌面，CPython 3.14.5 的 venv，Maison 3.1.0（`9c08d1e3`）。

**期望行为**　在 Windows 上，宿主通过虚拟环境的 `python.exe -m hylyre session start` 启动后台设备会话时，用户桌面全程无新增可见终端窗口或标签页，也不会闪窗、抢焦点。启动命令退出后，后台会话仍可连接，设备操作和正常停止均能完成。

**影响**　弹出的空白窗口关联着正在运行的 Hylyre 设备会话。用户关闭该控制台时，Windows 会通知附着进程退出；如果 daemon 随之结束，依赖这次会话的真机测试就会中途失败。长时间无人值守运行中，正式真机测试每次经这条路径新建会话，都可能再次弹窗并抢走前台焦点。本次现场确认了弹窗和界面树写出；关窗导致测试中断属于影响分析，现场未做关窗试验。[Windows 控制台关闭行为](https://learn.microsoft.com/en-us/windows/console/ctrl-close-signal)

## 现场证据

2026-11-20，宿主 `SimulatedWalletForHmos` 正在处理银行卡开卡需求。以下为宿主本地时间（UTC−05:00）。

| 时间 | 观测 |
|---|---|
| 10:58:49 | 主会话执行 `npm run adhoc-device-test -- --bundle com.example.simulatedwallet --dump-ui-only`。这个入口在抓取当前界面前调用 `hylyre session start`。 |
| 10:58:57 | 出现两层 `python.exe -m hylyre session daemon`，PID 依次为 35736、24668。同秒出现的 `conhost.exe`（PID 44576）以 24668 为父进程。 |
| 10:59:10 | 界面树 `dump-ui-20261120-105857.json` 写出，大小为 126460 字节。 |
| 10:59:29 | 用户截图中仍有可见的空白 Windows Terminal 窗口。现场读取到的窗口标题指向宿主的 `.hylyre\venv\Scripts\python.exe`。 |

本次界面抓取成功，后台窗口却持续可见。宿主实际安装的 `hylyre/cli/commands/session_cmd.py` 与 Maison 随包分发的同一文件 SHA-256 一致，为 `d3afb1d1b63fe30f676607eafe1a2a87aad3664a867faf8b26c5dd51f47312f4`。

## 排查定位

- **Maison 启动第一层 Python。** `harness/scripts/utils/adhoc-dump-ui.ts:49` 发起 `session start`，`profiles/hmos-app/harness/hylyre-spawn.ts:111` 调用 Node `spawnSync`，已设置 `windowsHide: true`。
- **Hylyre 启动守护进程。** 在 Hylyre 源码 `hylyre/cli/commands/session_cmd.py:65–82`，`run_session_start` 用 `sys.executable` 执行 `-m hylyre session daemon`，将三个标准流接到 `DEVNULL`。Windows 分支同时传入 `DETACHED_PROCESS`、`CREATE_NEW_PROCESS_GROUP` 和 `CREATE_NO_WINDOW`。微软文档明确说明，与 `DETACHED_PROCESS` 同用时，Windows 会忽略 `CREATE_NO_WINDOW`。[Windows 进程创建标志](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags)
- **venv 启动器还有一次进程创建。** CPython 3.14.5 的 Windows venv 启动器会再启动实际解释器，其 `CreateProcessW` 调用的创建标志为 `0`。这与现场的进程关系相符。请在这条完整链上验证修法，具体启动参数由 Hylyre 选择。[CPython 3.14.5 启动器源码](https://github.com/python/cpython/blob/v3.14.5/PC/venvlauncher.c#L418-L420)

**参考修法（供 Hylyre 选择）**

1. 在 Windows 的 `Popen` 调用中去掉 `DETACHED_PROCESS`，仅保留 `CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`，使无窗口标志生效。用实际 venv 验证启动器拉起底层解释器时也全程无可见窗口。
2. 保留调用方现有的 `python.exe -m hylyre session start` 入口，仅在内部用同一 venv 的 `Scripts\pythonw.exe` 启动 daemon。启动回执和退出码仍由外层 CLI 返回。

两种方案均以文末“桌面表现、后台可用、正常退出”三项 Windows 实测结果判定。

## 独立复现

准备 Windows 桌面、Node.js、一台可供 Hypium 抓取界面的测试设备，以及装有 Hylyre 0.6.1 的 CPython 3.14.5 虚拟环境。在含该 venv 的工程根目录用 PowerShell 执行下例。新临时目录确保走到创建 daemon 的路径；其他 venv 布局只需替换第一行路径。

```powershell
$py = (Resolve-Path '.hylyre\venv\Scripts\python.exe').Path
$caseDir = New-Item -ItemType Directory -Path (Join-Path $env:TEMP ("hylyre-console-" + [guid]::NewGuid()))
Push-Location -LiteralPath $caseDir.FullName
try {
    # 模拟宿主隐藏第一层 Python，并捕获其输出。
    node -e "const r=require('node:child_process').spawnSync(process.argv[1],['-m','hylyre','session','start'],{windowsHide:true,encoding:'utf8'});process.stdout.write(r.stdout||'');process.stderr.write(r.stderr||'');process.exitCode=r.status??1" $py
    if ($LASTEXITCODE -ne 0) { throw 'session start failed' }
    # 此时 Node 和执行 session start 的 Python 都已退出。
    & $py -m hylyre session status
    & $py -m hylyre dump-ui --session .hylyre/session.json --out ui.json
} finally {
    if (Test-Path -LiteralPath '.hylyre/session.json') { & $py -m hylyre session stop }
    Pop-Location
}
```

从执行 `start` 前开始观察桌面，持续至 `stop` 退出。宿主侧对应的复验入口是 `adhoc-device-test --dump-ui-only`。

## 验收与回传

| 验收项 | 通过条件 |
|---|---|
| 桌面表现 | 从全新会话启动至停止，无新增可见终端窗口或标签页、无瞬时闪窗、无抢焦点。用实际 Windows 桌面观察或短录屏核实。进程列表用于定位，窗口是否可见以桌面为准。 |
| 后台可用 | `session start` 退出码为 0。独立执行的 `session status` 返回 `alive: true`、`ping_ok: true`，随后 `dump-ui --session .hylyre/session.json --out ui.json` 返回 0 并写出可解析的真实界面树。 |
| 正常退出 | `session stop` 成功，本次 daemon 进程退出，本次会话文件清理。 |

请 Hylyre 侧回传修复提交或可集成版本、实测 Windows / Python / Hylyre 版本，以及上表三项的结果。Maison 侧收到修复版本后，通过既有发布件集成，在宿主重复界面抓取并确认桌面表现。
