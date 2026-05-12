# Design: add-cert-bootstrap

## Decisions

- **入口**：复用 `hylyre/drivers/lyrebird/cert_bootstrap.py` 中的指令生成；增量为 **可执行步骤**（子进程 `hdc`）与 **退出码约定**（成功 / 需人工 / 不支持）。
- **输入**：mitmproxy 默认 CA 路径（`~/.mitmproxy/mitmproxy-ca-cert.pem`）或 `HYLYRE_MITM_CA`；设备序列号 `--serial`。
- **兼容**：与 Lyrebird 版本解耦；仅依赖 hdc + 用户证书安装能力。

## Risks

- OS 大版本升级后「设置」路径变化 → 以探测失败降级到 Markdown 清单。
- 企业策略禁止用户 CA → 文档标明 Skill 6 场景需预置合规代理。
