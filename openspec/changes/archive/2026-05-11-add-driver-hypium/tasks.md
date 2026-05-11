# Tasks: add-driver-hypium

## P1.1 Base

- [x] 1. `UiDriverBase`：`connect/close/start_app/touch/input_text/screenshot`
- [x] 2. 参数校验：`touch` 三者择一（坐标对 / `by_text` / `by_id`）

## P1.2 Hypium

- [x] 3. `HypiumDriver` 懒加载 + `asyncio.to_thread` 包装
- [x] 4. `install_app` 封装（可选，由 CLI/device 路径使用）

## P1.3 HDC CLI helpers

- [x] 5. `hdc list targets` / `hdc install` 封装与单测（subprocess mock）

## P1.4 CLI

- [x] 6. `hylyre device list|install`
- [x] 7. `hylyre ai tap|input`（结构化；非 VLM）

## P1.5 Self-test

- [x] 8. `FakeUiDriver` + L2 契约测试
- [x] 9. `HypiumDriver` L1 mock 测试
- [x] 10. L3 假驱动工作流集成测试
- [x] 11. CLI Typer 测试（device/ai mock）
- [x] 12. CI：`pytest --cov=hylyre --cov-fail-under=70`

## P1.6 Verify

- [x] 13. 真机烟测：`hylyre device list` + `hylyre ai tap --x … --y …`（2026-05-11，Windows + USB 真机，Hypium uitest/agent 自举成功）
