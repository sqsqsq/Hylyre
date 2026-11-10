## Why

Hylyre 0.5.1 接受 `.png` 截图路径后可能写入 JPEG 并报告成功，导致 Maison 等消费方无法按声明格式读取；失败诊断也存在相同问题。截图格式识别、有效性检查和安全落盘缺少统一实现，需要在 0.5.2 完整修复。

输入依据：[0.5.2 需求文档](../../../../hylyre-0.5.2-截图文件编码与扩展名一致性修复需求.md)。本提案只描述待实施工作，不代表代码已修复或版本已发布。

## What Changes

- 新增共享图像模块，统一 PNG/JPEG 签名识别、目标后缀解析、图像结构检查和完整解码、必要转码及原子保存。
- CLI 一次性与会话截图、失败诊断截图均遵守请求路径与实际编码一致的契约；诊断继续使用 `.png`。
- **BREAKING**：不支持的后缀或无后缀不再自动改名，而是在采集前明确拒绝；无效截图不再作为成功文件或附件输出。
- CLI 字节接口、守护进程、MCP 和 VLM 使用相同的 MIME 识别规则；统一完整校验并返回真实 MIME，损坏、截断和未知格式均报错，不再默认 PNG；纯字节接口保持原有返回形态。
- Pillow 声明为核心运行依赖；修正现有损坏 PNG 测试素材，并增加真实图像、入口接线及失败安全性验证。
- 实施完成后发布 0.5.2 schema 2 源码发布件，完成干净安装验证、发布清单校验和交付报告。

## Capabilities

### New Capabilities

- `screenshot-io`: 跨入口的截图编码、路径、有效性、MIME、失败安全性以及可安装发布契约。

### Modified Capabilities

无。现有 driver 栅格字节接口、CLI/MCP 调用协议和失败诊断规则保持；新增能力集中补齐其图像输出约束，不重复定义现有步骤与 trace 协议。

## Impact

- 实现：`hylyre/image_io.py`、`hylyre/cli/commands/loop_cmd.py`、CLI 帮助、`hylyre/api/failure_diag.py`、`hylyre/session/daemon.py`、`hylyre/mcp/server.py`、`hylyre/vlm/http_vlm.py`。
- 安装与版本：`pyproject.toml` 的核心依赖和版本、`hylyre/__init__.py` 版本；复用现有 `scripts/build_wheel.py --source` 与 `--verify`。
- 验证：图像单元测试、CLI/MCP/会话与诊断调用链、相关既有回归、发布件安装验证；修正 `tests/contract/fakes/fake_ui_driver.py` 和使用伪文件头作为成功图片的相关测试。
- 非目标：不改 Maison 或消费方代码、既有截图证据、Step Outcome/trace schema、selector、执行顺序和断言规则；不新增命令、MCP 参数、格式插件、状态管理或独立清单。不将 Hypium 内部 `.jpeg` 采集改成按调用方后缀采集。
- 权限边界：实现与发布限于 Hylyre；不包含向消费方仓库复制、部署、上传或改写历史证据的授权。提案本身不代表实施或发布已完成。
