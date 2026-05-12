# Proposal: add-cert-bootstrap

## Why

Lyrebird / mitmproxy 要求设备信任 MITM CA；手工步骤易错、难重复。需要在 **不阻塞主 CI** 的前提下，把「证书推到设备 + 引导安装」收敛为可脚本化路径，并与 `hylyre doctor` / 文档联动。

## What Changes

- 新增或扩展 CLI（例如 `hylyre mock trust-ca` / `hylyre device trust-mitm`）封装常见 `hdc file send` + 文档化回退。
- 设备侧安装随 HarmonyOS 版本差异大：优先自动化探测 + 失败时打印与 `mock cert` 一致的手工清单。
- 自测：L1 纯函数/命令拼装单测；真机烟测仍为可选（与 `add-driver-lyrebird` 任务 14 同类）。

## Non-goals（首版）

- 保证全机型无交互；不能保证所有安全策略下 silent 安装成功。
