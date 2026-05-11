"""MITM / HarmonyOS trust checklist (P2 placeholder; automation in add-cert-bootstrap)."""

from __future__ import annotations

from pathlib import Path


def mitm_trust_instructions(
    *,
    hdc_serial: str | None = None,
    ca_cert: Path | None = None,
) -> str:
    """Human-run steps until hdc+bm automation lands (see plan §7)."""
    lines = [
        "## HarmonyOS 设备信任 MITM / Lyrebird 证书（手工清单）",
        "",
        "1. 在一台已安装 **mitmproxy** 的机器上生成或导出 CA（如 `~/.mitmproxy/mitmproxy-ca-cert.pem`）。",
        "2. 将 PEM 转为设备可安装格式（若需要 CRT），用 **hdc file send** 推到设备可访问路径。",
        "3. 在设备 **设置 → 安全 → 加密与凭据 → 从存储安装**，安装 CA。",
        "4. 确认 Lyrebird / mitmproxy **代理端口**（默认与 `--proxy` 一致）已在 Wi‑Fi APN 或应用侧配置。",
        "",
    ]
    if ca_cert:
        lines.append(f"- 参考证书路径：`{ca_cert}`")
    if hdc_serial:
        lines.append(
            f"- 多设备时使用 `hdc -t {hdc_serial} file send ...` 指定序列号。"
        )
    lines.append("")
    lines.append(
        "后续迭代：在 `add-cert-bootstrap` 中收敛尝试 `hdc` + 系统 `bm`/`aa` "
        "自动化安装（失败则回退到本清单）。"
    )
    return "\n".join(lines)
