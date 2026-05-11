# Tasks: add-mvp-skeleton

## 8.1 Environment

- [x] 1. Python ≥3.10、Node ≥20.19、npm 检测（文档：`docs/progress.md`；本机若无 Python 需自行安装后跑 pip/pytest）
- [x] 2. 不满足时指引见 progress / doctor 输出

## 8.2 Scaffold

- [x] 3. `pyproject.toml` 与 entrypoint
- [x] 4. `hylyre/` 包目录与 `__init__.py`
- [x] 5. `hylyre/cli/__main__.py` 子命令占位 + `report verify`
- [x] 6. `hylyre/cli/commands/doctor.py` 实装

## 8.3 Test infra

- [x] 7. `tests/` 分层与 README
- [x] 8. `tests/unit/test_cli_help.py`
- [x] 9. `tests/schema/test_contracts_loadable.py`
- [x] 10–13. contracts + harness 占位
- [x] 14–15. `.github/workflows/ci.yml` + `compat-framework.yml`

## 8.4 OpenSpec

- [x] 16. `npm install -g @fission-ai/openspec`
- [x] 17. `openspec init . --tools cursor,codex,claude --force`
- [x] 18. `.cursor/commands`、skills 已生成；`openspec/project.md` 本提交补全

## 8.5 Charter + change

- [x] 19. `openspec/project.md`
- [x] 20. 本目录 proposal/design/tasks + `specs/*`

## 8.6–8.7 Docs

- [x] 21. `docs/progress.md`（随构建更新）
- [x] 22. `README.md` 扩写

## 8.8 Verify

- [x] 23. `pip install -e ".[dev]"`（Python 3.12.10：`winget install Python.Python.3.12`；`python`/Scripts 建议加入用户 PATH）
- [x] 24. `hylyre --help` 与子命令（`python -m hylyre` 或 `%LocalAppData%\Programs\Python\Python312\Scripts\hylyre.exe`）
- [x] 25. `hylyre doctor`（已修复 Typer `doctor` 与模块同名冲突）
- [x] 26. `pytest` 全绿（15 passed，2026-05-11）
- [x] 27. 本 `tasks.md` 8.1–8.7 勾选
- [x] 28. `openspec list` 含 `add-mvp-skeleton`
- [x] 29. workflow 文件已存在
- [x] 30. git commit（`49627f7`，含 `.claude` / `.codex`）
