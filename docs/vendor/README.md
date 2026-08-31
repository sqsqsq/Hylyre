# docs/vendor — 下游提出的规格需求归档

本目录归档**由下游消费方（framework / 宿主工程）提给 Hylyre 的规格需求与修复需求原件**，按提出时的原样保存，作为历史记录。

## 放什么

- 下游（如 Maison / SimulatedWalletForHmos）提出的协议、契约、行为需求文档；
- 针对具体版本的缺陷修复需求书。

命名沿用需求文档自身的约定：

```text
hylyre-<版本>-<主题>需求.md      # 版本相关，如 hylyre-0.5.0-执行观测与结果反馈协议重构需求.md
hylyre-<主题>需求.md             # 跨版本主题
```

## 不放什么

- **Hylyre 自己写给下游的**集成/移交文档 → 留在 `docs/`（如
  [`framework-vendor-bundle.md`](../framework-vendor-bundle.md)、
  [`downstream-harness-requests.md`](../downstream-harness-requests.md)、
  [`framework-simulated-wallet-hylyre.md`](../framework-simulated-wallet-hylyre.md)）；
- **Hylyre 侧的设计与实现决策** → 走 OpenSpec change（`openspec/changes/<id>/`）；
- **对外冻结的机器契约** → `hylyre/contracts/`（随包发布，是 SSOT）。

## 归档纪律

需求原件**只增不改**。落地过程中发现需求内部矛盾或无法实现时，不修改原件去迁就实现，而是在对应的 OpenSpec change 的 `design.md` 里记录解释决定与裁决——原件保持可追溯，决策有独立出处。

## 已归档

| 文档 | 目标版本 | 落地 |
|---|---|---|
| [hylyre-0.5.0-执行观测与结果反馈协议重构需求.md](hylyre-0.5.0-执行观测与结果反馈协议重构需求.md) | 0.5.0 | `openspec/changes/step-outcome-protocol-v1/` |

> 该需求文档引用的 `hylyre-断言与证据完整性需求.md` 与
> `hylyre-0.4.1-结构化Selector身份脱敏修复需求.md` 提出时未归档到本仓，
> 目前只存在于下游仓库；其落地结果见 0.4.0 / 0.4.1 的提交历史。
