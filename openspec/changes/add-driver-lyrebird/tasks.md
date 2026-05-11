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
- [x] 13. 证书自动化已拆为独立 change **`add-cert-bootstrap`**（见 `openspec/changes/add-cert-bootstrap/`，实装以该目录 `tasks.md` 为准）

## P2.6 真机 / 进程烟测（可选）

- [x] 14. **`mock start` / `mock status` / `mock stop` 路径**：CLI + 单测已覆盖；**真 Lyrebird 进程**需本机 `pip install -e ".[mock]"`（或等价安装 `lyrebird`）。**Windows**：依赖 `netifaces` 等可能需 [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)，否则 pip 构建失败——步骤与阻塞记录见 `docs/progress.md`。
