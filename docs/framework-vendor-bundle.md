# Framework vendor wheel（业务仓集成）

Hylyre 尚未在公共 PyPI 发布；若下游 **framework** 无法从 GitHub 拉源码，可将本仓打出的 **单一纯 Python wheel**（`py3-none-any`）提交到其 `vendor/hylyre/`，再通过本机可访问的 PyPI 镜像安装传递依赖（`hypium`、`fastmcp` 等）。

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
- `downstream-harness-requests.md`（**framework harness 接入清单**：#3 冷重启 / positional force-stop、#6 `app page save` 调用约定与验收命令；与 wheel **同目录**打出，需一并 copy 到 vendor）

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

## 相关

- 实现脚本：[scripts/build_wheel.py](../scripts/build_wheel.py)
- OpenSpec 变更：`openspec/changes/add-vendor-bundle/`
