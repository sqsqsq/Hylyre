# Tasks: add-driver-lyrebird

## P2.1 契约

- [x] 1. `MockControllerBase`（start/stop/activate/deactivate/status/flows/export）
- [x] 2. `FakeMockController` + L2 契约测试

## P2.2 Lyrebird

- [x] 3. `LyrebirdController` + `LyrebirdApiError`
- [x] 4. `require_lyrebird_distribution()` 懒校验
- [x] 5. PID 文件：`default_pid_path` / `terminate_pid`（Windows `taskkill`）

## P2.3 CLI

- [x] 6. `hylyre mock start|stop|status|activate|deactivate|capture|cert`
- [x] 7. 更新 `test_cli_help` mock 子命令

## P2.4 自测

- [x] 8. respx 覆盖 Lyrebird HTTP（无真进程）
- [x] 9. `mock` Typer 单测（patch）
- [x] 10. L3 `FakeMockController` 工作流
- [x] 11. CI 覆盖率仍 ≥ 70%

## P2.5 证书（占位）

- [x] 12. `cert_bootstrap.mitm_trust_instructions` + `mock cert`
- [ ] 13. `add-cert-bootstrap`：hdc + 系统 CA 安装自动化（后续 change）

## P2.6 真机 / 进程烟测（可选）

- [ ] 14. 本机安装 `hylyre[mock]` 后 `mock start` + `mock status` + `mock stop`
