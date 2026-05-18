---
name: hylyre vendor bundle
overview: 面向 framework 集成的前置工作：在 Hylyre 仓内新增一个最小化的发布脚本与文档，仅产出 hylyre 自身的纯 Python wheel（py3-none-any，跨所有 OS）。framework 仓 cp 这一个 wheel 到 vendor 目录后即可 `pip install`；传递依赖（hypium / fastmcp / pydantic 等）由 framework 侧机器的 PyPI 镜像现场拉，不在本仓打包。同时修正原 plan 第三点的偏差。
todos:
  - id: openspec_proposal
    content: openspec/changes/add-vendor-bundle/ 下新建 proposal.md / tasks.md / specs/packaging/spec.md（声明 'packaging' capability、build_wheel.py 的 CLI 与产物契约）
    status: completed
  - id: build_wheel_py
    content: 新增 scripts/build_wheel.py：用 `pip wheel . --no-deps -w dist/release/` 产出 1 个 hylyre-*-py3-none-any.whl，并写 release.manifest.json（hylyre_version / sha256 / size / generated_at / python / pip 版本）
    status: completed
  - id: verify_subcommand
    content: build_wheel.py 同文件追加 --verify <dir> 子命令：读 release.manifest.json，重算 wheel sha256 比对，不一致即 exit 2
    status: completed
  - id: thin_wrappers
    content: 新增 scripts/build-wheel.ps1 与 scripts/build-wheel.sh：仅选解释器 + 转发参数到 build_wheel.py，避免双实现漂移
    status: completed
  - id: framework_vendor_doc
    content: 新增 docs/framework-vendor-bundle.md：面向 framework 仓维护者的 3 分钟手册（何时跑 / 一条命令 / cp 到 framework / 校验 / 升级流程）
    status: completed
  - id: packaging_tests
    content: 新增 tests/packaging/test_build_wheel.py：纯函数单测 + 一个真实端到端 case（运行 build_wheel，断言 wheel 与 manifest 出现，verify 通过）
    status: completed
  - id: ci_release_job
    content: 微调 .github/workflows/ci.yml：新增一个 build-wheel job（ubuntu-latest，python 3.12）跑 `python scripts/build_wheel.py --clean` + verify，纯烟测不上传 artifact
    status: completed
  - id: readme_agents_short
    content: README.md 与 AGENTS.md 追加一段“发布 wheel 给 framework”最短命令，指向 docs/framework-vendor-bundle.md
    status: completed
  - id: local_smoke
    content: 本地验证：pytest 过 + 跑一次真实 build_wheel + verify + 临时 venv `pip install <wheel>` + `hylyre doctor` 通过（联网可装传递依赖）
    status: completed
isProject: false
---

## 关键反转（先讲清楚为什么砍掉原方案的"大头"）

原 plan 第三点假设"framework 仓所在环境完全离线、所有依赖必须 vendor"，所以设计了完整 wheelhouse + 多平台 cp + sha256 manifest。但你刚才纠正：

- 真实工程能访问 PyPI（含国内镜像），**只是**访问不到 GitHub 这类境外仓库。
- Hylyre 在 PyPI 没发布、只能从 GitHub 拿源码 → **这才是 framework 真正的"拉不到"问题**。
- Hypium / fastmcp / pydantic / httpx 等传递依赖**都在 PyPI 上**，国内源也都同步过 → 不需要本仓 vendor。
- Hylyre 自身是**纯 Python**（[pyproject.toml](D:/1.code/Hylyre/pyproject.toml) 无 C 扩展），产物会是 1 个 `hylyre-0.1.0-py3-none-any.whl`，**跨 OS+arch+Python 版本通用**。

所以 Hylyre 侧只需要做一件事：**把自己打成一个 wheel 发出来，让 framework 仓 vendor**。这比原方案小一个数量级。

## 修正原 plan 第三点的具体偏差

| 原 plan 描述 | 实际情况 | 新 plan 怎么做 |
|---|---|---|
| `scripts/build-bundle.{ps1,sh}` 内部 `pip download ".[device]"` 下载所有传递依赖 | 不需要，PyPI 可达 | 砍掉 `pip download`；只 `pip wheel . --no-deps` |
| `bundle.manifest.json` 含 `wheels: [...]` 数组 + 每个 wheel 的 sha256 | 只有 1 个 wheel | manifest 只描述这一个 hylyre wheel |
| vendor 目录按 `<os>-<arch>` 分子目录 | hylyre 是 `py3-none-any.whl`，跨所有平台通用 | framework 那侧 vendor 目录扁平化，无需平台子目录 |
| `python -m build` | 不是当前 dev 依赖，且不需要 sdist | 直接 `pip wheel .`，零额外依赖 |
| 框架侧 `--store-dir doc/app-cache` 传给 `hylyre run --plan` | `hylyre run --plan` 根本不接受 `--store-dir`（核对 [hylyre/cli/__main__.py:178-374](D:/1.code/Hylyre/hylyre/cli/__main__.py)）；`--store-dir` 只在 `hylyre app page save/load/list/find` 上 | 不在本仓改 CLI；framework 侧那条要删/改语义（见末尾"对 framework plan 的连带建议"） |
| OpenSpec change 没提 | Hylyre 仓走 [`openspec`](D:/1.code/Hylyre/openspec) 工作流 | 本期改动走一个 change proposal |

## 一、改动清单（最终落在 Hylyre 仓 = `D:\1.code\Hylyre`）

```
D:\1.code\Hylyre\
├── openspec\changes\add-vendor-bundle\          # 新增
│   ├── proposal.md
│   ├── tasks.md
│   └── specs\packaging\spec.md
├── scripts\
│   ├── build_wheel.py                           # 新增：核心实现（Python，本仓已有 3.10+）
│   ├── build-wheel.ps1                          # 新增：Windows 入口（薄封装）
│   └── build-wheel.sh                           # 新增：POSIX 入口（薄封装）
├── docs\
│   └── framework-vendor-bundle.md               # 新增：framework 维护者操作手册
├── tests\packaging\                             # 新增
│   ├── __init__.py
│   └── test_build_wheel.py
├── README.md                                    # 微编辑：在"快速开始"下追加一段"发布 wheel 给 framework"短指引
├── AGENTS.md                                    # 微编辑：附加一行最短命令
└── .github\workflows\ci.yml                     # 微编辑：新增 build-wheel job
```

**注意**：不再改 `pyproject.toml`（原 plan 想加 `build>=1.2` 到 dev extras 也不需要了，主路径走 `pip wheel`）。

## 二、`scripts/build_wheel.py` 行为约定

> 选择 Python 而非纯 shell：① 跨平台同源，避免 `.ps1` + `.sh` 双实现漂移；② 可被 `pytest` 单测；③ 后续 framework CI 想自动同步时也能直接调。

入参（CLI，使用 `argparse`，零额外依赖）：

```text
python scripts/build_wheel.py
  [--out-dir dist/release]   # 默认 dist/release（已在 .gitignore）
  [--clean]                  # 清空 out-dir 后再打
  [--verify <dir>]           # 子模式：读 release.manifest.json 重算 sha256 比对
```

主流程（默认模式）：

1. **环境自检**：`platform`、`sys.version_info`、`pip --version`、`subprocess.run(["pip","--version"])` 探活。
2. **打 hylyre 自身**：在 repo 根执行  
   `python -m pip wheel . --no-deps -w <out-dir>`  
   产物为 `hylyre-<version>-py3-none-any.whl`（1 个文件）。
3. **写 `release.manifest.json`** 到 `<out-dir>/`：
   ```json
   {
     "schema": 1,
     "hylyre_version": "0.1.0",
     "wheel": {
       "filename": "hylyre-0.1.0-py3-none-any.whl",
       "sha256": "<hex>",
       "size_bytes": 123456
     },
     "generated_at": "2026-05-18T10:00:00Z",
     "generator": {
       "python": "3.12.x",
       "pip": "24.x",
       "platform": "Windows-10-AMD64"
     },
     "note": "Pure-Python wheel (py3-none-any). Install with: pip install <filename>; pip will fetch transitive deps (hypium/fastmcp/etc.) from PyPI."
   }
   ```
4. stdout 打印两件事：① wheel 的绝对路径；② "下一步 cp 到 framework"的命令片段。

`--verify <dir>` 子模式：

- 读 `<dir>/release.manifest.json`；
- 在同目录找 `wheel.filename`，算 sha256 比对；
- 不一致 → `exit 2` + stderr 给出 expected / actual。

退出码：

- `0`：build / verify 成功；
- `1`：`pip wheel` 失败（透传 pip stderr）；
- `2`：verify 失败；
- `3`：参数错误（如 `--verify` 指向的目录不存在 / manifest 缺失）。

`.ps1` 和 `.sh` 仅做选解释器 + 转发参数。

## 三、`docs/framework-vendor-bundle.md` 大纲

面向"framework 仓维护者"，目标是 3 分钟内完成发布。

1. **何时跑**：Hylyre 仓打 tag、或 framework 那边的 doctor 报告 hylyre wheel 缺失/版本过旧时。
2. **一条命令产出**：
   ```pwsh
   cd D:\1.code\Hylyre
   pip install -e ".[dev]"                 # 仅首次需要（确保仓内可跑）
   python scripts/build_wheel.py --clean
   # 产出：D:\1.code\Hylyre\dist\release\hylyre-0.1.0-py3-none-any.whl
   #       D:\1.code\Hylyre\dist\release\release.manifest.json
   ```
3. **同步到 framework 仓**：
   ```pwsh
   $src = "D:\1.code\Hylyre\dist\release"
   $dst = "D:\1.code\SimulatedWalletForHmos\framework\profiles\hmos-app\vendor\hylyre"
   New-Item -ItemType Directory -Force -Path $dst | Out-Null
   Remove-Item -Force "$dst\*.whl","$dst\release.manifest.json" -ErrorAction Ignore
   Copy-Item "$src\hylyre-*.whl" $dst
   Copy-Item "$src\release.manifest.json" $dst
   ```
4. **本机校验**：
   ```pwsh
   python D:\1.code\Hylyre\scripts\build_wheel.py --verify $dst
   ```
5. **framework 那侧装机的预期**（仅作澄清，不在本仓实现）：
   ```pwsh
   pip install "<vendor>\hylyre-*.whl" "hylyre[device,mcp]" \
       --extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple
   # ↑ 关键：先指向本地 wheel 让 pip 找到 hylyre 本体；
   #   传递依赖 (typer/pydantic/hypium/fastmcp/...) 由 pip 从 PyPI 拉
   ```
6. **升级流程**：bump `pyproject.toml.version` → 重跑 step 2 → 重跑 step 3 → framework 仓 commit 新 wheel。manifest 里的 `hylyre_version` 字段供 framework doctor 比对。
7. **跨平台**：因为是 `py3-none-any.whl`，**不需要**在不同 OS 上各打一份；在任何能跑 Python 3.10+ 的机器上打一次即可。

## 四、`tests/packaging/test_build_wheel.py` 自检要点

- 单元：纯函数（`compute_sha256`、`build_manifest`、`format_cp_hints`）的输入输出。
- 集成：在 `tmp_path` 里真实跑 `pip wheel . --no-deps`（用本仓自己当源），断言：
  - 产物含 1 个 `hylyre-*-py3-none-any.whl`；
  - `release.manifest.json` 字段齐全且 `wheel.sha256` 与文件计算一致；
  - `--verify` 子命令返回 0；
  - 故意改一个 byte 后 `--verify` 返回 2 且 stderr 含 "sha256 mismatch"。
- 标 `@pytest.mark.slow`（实际跑 pip wheel 需要 ~3 秒），不进默认 `pytest -q`，由 ci.yml 的专属 job 触发。

## 五、`.github/workflows/ci.yml` 微调

新增 job（附加到现有 matrix 之后）：

```yaml
build-wheel:
  runs-on: ubuntu-latest
  needs: test
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: "3.12" }
    - name: Install build env
      run: pip install -e ".[dev]"
    - name: Build wheel
      run: python scripts/build_wheel.py --clean
    - name: Verify wheel
      run: python scripts/build_wheel.py --verify dist/release
```

不上传 artifact（本期烟测目的），后续做 release tag 自动化时再加 `actions/upload-artifact`。

## 六、OpenSpec change 提案（`openspec/changes/add-vendor-bundle/`）

- `proposal.md`：背景 = framework 仓访问不到 GitHub，需要本仓提供单文件 wheel 供 vendor；范围 = 仅新增 1 个脚本 + 文档 + 单测 + 1 个 CI job；非目标 = 不改任何 hylyre 业务代码 / CLI / 依赖声明。
- `tasks.md`：四个任务（脚本实现 → 单测 → 文档 → CI job）。
- `specs/packaging/spec.md`：以 `### Requirement` 形式声明 `build_wheel.py` 的对外契约（CLI 入参、产物文件名规则、manifest schema v1、退出码语义）。

## 七、验证步骤（结束前必须跑通）

```pwsh
cd D:\1.code\Hylyre
pip install -e ".[dev]"
pytest tests/packaging -q -m slow
python scripts/build_wheel.py --clean
# 期望：dist/release/ 下出现 hylyre-*-py3-none-any.whl + release.manifest.json
python scripts/build_wheel.py --verify dist/release
# 期望：exit 0

# 模拟 framework 装机（联网，模拟国内 PyPI 镜像可达）
python -m venv $env:TEMP\h-smoke
$env:TEMP\h-smoke\Scripts\python.exe -m pip install `
  dist/release/hylyre-0.1.0-py3-none-any.whl "hylyre[device,mcp]" `
  --extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple
$env:TEMP\h-smoke\Scripts\python.exe -m hylyre doctor
# 期望：hylyre import 成功、doctor 通过；
#       site-packages/hylyre/ 下能看到完整源码（验证"wheel 内含源码"）
```

## 八、不做的（明确划线）

- **不在** Hylyre 仓 vendor 任何第三方 wheel（hypium / fastmcp / lyrebird 等都让 framework 那侧从 PyPI 拉）。
- **不**改 hylyre 任何 CLI 行为、命令、参数（包括 `run --plan` / `app page`）。
- **不**发布到公网 PyPI（hylyre 当前还未稳定到对外发布的标准；framework 仓 vendor wheel 已足够覆盖业务需求）。
- **不**承担 framework 仓的 `vendor/hylyre/` 目录维护；本仓只提供"打包 + 校验 + 文档 + 一条 cp 命令"。
- **不**接 lyrebird/mock 链路。

## 九、对原 framework plan 的连带建议（不在本期落地，给你确认后下一份 framework plan 用）

1. **vendor 目录大瘦身**：原 plan 4.1 / 4.10 的 `vendor/hylyre/wheels/<os>-<arch>/*.whl` 全部砍掉，改为单文件结构：
   ```
   framework/profiles/hmos-app/vendor/hylyre/
   ├── hylyre-0.1.0-py3-none-any.whl
   ├── release.manifest.json
   └── README.md
   ```
   `.gitignore` 不再需要排除 wheels（vendor 整个目录入库，<1 MB）。
2. **framework 安装策略调整**（原 plan 4.3 `ensureHylyreReady`）：从"`pip install --no-index --find-links`"改为"`pip install <vendored wheel> "hylyre[device,mcp]"` + 默认让 pip 走 PyPI / 用户环境的 `pip.conf` 国内镜像"。完全离线场景退化为"装机失败 → doctor 提示用户配置 PyPI 镜像"。
3. **`framework.config.json > tools.hylyre`** 字段精简：删 `bundle_dir`、`platform` 等多平台元数据；保留 `vendor_dir` / `venv_dir` / `auto_install`。
4. **`--store-dir doc/app-cache`** 这一段（原 plan 4.3）要从 `hylyre run --plan` 调用串里去掉——`run` 子命令根本不接受这个参数。`doc/app-cache` 改名为 `app_snapshot_cache_dir`，仅在 agent 主动调 `hylyre app page save/load/find` 时由 framework 透传 `--store-dir`。
5. **framework doctor**：读 `vendor/hylyre/release.manifest.json` 取 `hylyre_version`，与 `pip show hylyre` 比对，不一致就提示"重跑 Hylyre 仓 `python scripts/build_wheel.py` 后 cp"，指引点击 [docs/framework-vendor-bundle.md](D:/1.code/Hylyre/docs/framework-vendor-bundle.md)。
