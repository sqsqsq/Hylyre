# Framework vendor bundle（业务仓集成）

Hylyre 尚未在公共 PyPI 发布；若下游 **framework** 无法从 GitHub 拉源码，可将本仓打出的发布件提交到其 `vendor/hylyre/`，再通过本机可访问的 PyPI 镜像安装传递依赖（`hypium`、`fastmcp` 等）。两种发布模式**并存**，下游按 manifest `schema` 区分消费：

- **wheel 模式**（schema 1）：单一纯 Python wheel（`py3-none-any`）；
- **明文源码树模式**（schema 2，`--source`）：`src/` 源码目录，供**禁止提交 `.whl` / `.tar.gz` 等二进制归档**的公司仓库使用（Hylyre 包本体全部是文本文件），见下文「[明文源码树发布](#明文源码树发布schema-2)」。

## 何时运行

- 本仓 **bump** `pyproject.toml` 的 `version` 后；
- 或下游需要同步固定版本的 hylyre 工件时。

## 一条命令（在 Hylyre 仓库根）

```powershell
pip install -e ".[dev]"
python scripts/build_wheel.py --clean
```

产物（默认 `dist/release/`，目录已在 `.gitignore`）：

- `hylyre-<version>-py3-none-any.whl`
- `release.manifest.json`（含 `sha256`，供下游校验；`integration_docs` 列出 harness 移交文档）
- `downstream-harness-requests.md`（**framework harness 接入清单**：冷重启 / page save / personal-setup DevEco 路径；与 wheel **同目录**打出，需一并 copy 到 vendor）

POSIX 也可用：`./scripts/build-wheel.sh --clean`

## 校验 manifest 与 wheel 一致

```powershell
python scripts/build_wheel.py --verify dist/release
```

退出码：`0` 成功；`2` sha256 不匹配；`3` 参数或文件缺失。

## 同步到下游 framework 仓（示例路径）

```powershell
$src = "D:\1.code\Hylyre\dist\release"
$dst = "<YourFramework>\framework\profiles\hmos-app\vendor\hylyre"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Remove-Item -Force "$dst\hylyre-*.whl","$dst\release.manifest.json","$dst\downstream-harness-requests.md" -ErrorAction Ignore
Copy-Item "$src\hylyre-*.whl" $dst
Copy-Item "$src\release.manifest.json" $dst
Copy-Item "$src\downstream-harness-requests.md" $dst
python D:\1.code\Hylyre\scripts\build_wheel.py --verify $dst
```

同步后请阅读 **`vendor/hylyre/downstream-harness-requests.md`**（或 `dist/release/` 内同名文件）：说明 Hylyre-core 已交付的 CLI 与 **framework 仓仍需改的 harness 项**（非 wheel 内文档，需随发布件一起分发）。

## 下游安装（需能访问 PyPI 或镜像）

`py3-none-any` **与 OS 无关**；在任意平台打一次即可给全团队使用。

```powershell
pip install ".\hylyre-0.1.0-py3-none-any.whl" "hylyre[device,mcp]" `
  --extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

说明：先指向本地 wheel 解析 `hylyre` 包本身；`device` / `mcp` 等 extras 及传递依赖由 pip 从索引拉取。

## 明文源码树发布（schema 2）

### 构建与校验（在 Hylyre 仓库根）

```powershell
python scripts/build_wheel.py --source --clean
python scripts/build_wheel.py --verify dist/release-src
```

产物（默认 `dist/release-src/`）：

- `src/`：`pyproject.toml`、`README.md`（pyproject `readme` 引用，安装必需）与 `hylyre/` 包源码（**含 `contracts/` package-data**：`*.json` / `*.yaml` / `*.yml` / `*.md`，`source.files` 完整声明，请勿当作“文档类文件”剔除）。排除 `__pycache__/`、`*.pyc`、`*.egg-info/`、`build/`、`tests/`
- `release.manifest.json`：schema 2，含 `source.files[]` 逐文件 `sha256` / `size_bytes` 与聚合值 `tree_sha256` / `file_count` / `total_bytes`
- `downstream-harness-requests.md`：integration_docs 机制照旧，需随发布件一并分发

`src/` 可被 `pip install <src路径>` 直接安装（PEP 517，`setuptools>=61` + `wheel` 后端）。`src/hylyre/api/planned_step_keys.py` 是下游步骤键集 SSOT，路径保持稳定。

### EOL 与 tree_sha256 算法（确定性）

发布件内所有文本文件统一 **LF 落盘**，`files[].sha256` 按 LF 字节计算——下游 git 若配置 `* text=auto eol=lf`，checkout 字节与 manifest 声明恒等，逐文件校验不会假漂移。构建期有兜底守护：staged 树内任何文件若仍含 CRLF（例如新增了归一化白名单之外的文本后缀），构建直接失败，避免 sha 漂移只在下游暴露。

`tree_sha256`：

1. 收集 `source.root`（即 `src/`）下全部文件，按 POSIX 相对路径（`/` 分隔）**字节序**升序排序；
2. 逐文件对落盘字节计算 sha256（hex 小写）；
3. 拼接每个文件的 `"<path>\n<sha256>\n"`，对拼接串的 UTF-8 字节整体计算 sha256。

### 同步到下游（复制清单）

`src/`（整目录）+ `release.manifest.json` + 移交文档：

```powershell
$src = "D:\1.code\Hylyre\dist\release-src"
$dst = "<YourFramework>\framework\profiles\hmos-app\vendor\hylyre"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Remove-Item -Recurse -Force "$dst\src" -ErrorAction Ignore
Copy-Item -Recurse "$src\src" "$dst\src"
Copy-Item -Force "$src\release.manifest.json" $dst
Copy-Item -Force "$src\downstream-harness-requests.md" $dst
python D:\1.code\Hylyre\scripts\build_wheel.py --verify $dst
```

### 校验语义（`--verify`，退出码同 wheel 模式）

- `src/` 子树**严格**：`source.files` 逐文件存在且 sha256 / size 匹配，`tree_sha256` / `file_count` / `total_bytes` 匹配，manifest `hylyre_version` 与 `src/pyproject.toml` 一致；`src/` 内存在 manifest **未声明**的文件 → 退出码 `2`（可抓误跑 in-tree build 落下的 `build/`、`*.egg-info/` 污染物）
- `src/` 之外（vendor 根一层）归下游所有，一律**不检测**——下游的 `README.md`、过渡期残留的 whl 等天然免检
- `integration_docs`：文件**存在则 sha 必须匹配**；文件缺失、或 manifest 中该字段整体缺失，均**放行**（覆盖源仓布局与下游发布件布局两种情况）

### 下游安装

```powershell
pip install "<vendor>\src" "hylyre[device,mcp]" --extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

前提：pip 从目录安装走 **PEP 517 build isolation**，镜像须能拉到 `setuptools>=61` 与 `wheel`（与「传递依赖走镜像」同一前提，无新增网络要求）。建议先把 `src/` **拷贝到临时目录再安装**，规避 pip ≥21.3 的 in-tree build 在 vendor 目录里生成 `build/`、`*.egg-info/`（未声明文件检测是这类污染的最后防线）。

## 相关

- 实现脚本：[scripts/build_wheel.py](../scripts/build_wheel.py)
- OpenSpec 变更：`openspec/changes/add-vendor-bundle/`、`openspec/changes/add-source-release/`
