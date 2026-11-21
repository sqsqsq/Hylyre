# Changelog

## 0.6.2 — 2026-11-20 — Windows 后台会话无窗口启动

- Windows 上的 `session start` 通过当前 Python 环境无窗口启动 daemon，避免虚拟环境启动器拉起解释器时出现额外终端窗口。

## 0.6.1 — 2026-11-14 — Markdown 计划字符串保真

- 修复 `parse_test_plan` 对整列替换 `<br/>`，导致合法 Shell/input JSON 字符串原文被改为空格。特殊保护仅用于测试步骤列的 JSON 字符串，保留转义引号、反斜杠、中英文分号、多步骤与标准 `\|` 管道转义。
- 其它列及步骤 JSON 字符串外 `<br/>` 仍为空格，不新增步骤分隔含义；现有反引号/围栏包装、其它换行标记写法和普通 Markdown 行为不变。真实表格入口回归覆盖原始 `printf '%s' '<br/>'`、Shell/input 精确往返、整格/混合包装与兼容反例。
- 产品版本更新为 0.6.1；历史版本、`hylyre.step-outcome/1`、trace schema `0.4-p0` 和独立 manifest schema 保持不变。

## 0.6.0 — 2026-11-14 — 常用设备操作

- 扩展 touch normal/long/double；新增拖拽、点到点滑动、原生 fling、pinch、双指/多点/连续轨迹、按键/组合键、清空/光标、属性/幂等勾选、应用查询/最近任务和结构化设备 Shell，贯通 CLI/MCP/plan/steps/session。
- 布尔过滤新增 checked/checkable/focused；clickable/enabled/scrollable 的显式 false 从忽略改成精确过滤，输入统一只接受 JSON 布尔。依赖旧忽略行为的调用应移除字段；布尔字符串应改成布尔。
- 计划 JSON 内分号/转义换行不再错误拆步，表格支持标准 `\|` 转义。查询不增加断言覆盖，无设备 fake 不制造属性/应用/Shell 事实。
- 属性查询/清空/勾选使用文本实际匹配节点；仅含checked/checkable/focused（含嵌套）的状态等待切到实际节点，其它旧rich等待及点击保留原升父语义。点击后状态确认异常保留已执行事实；不适用目标或手势边界违例归contract.invalid_step。HMOS三键不降级为两键，能力无法确认时阻塞。
- **兼容性**：产品版本更新为0.6.0，旧步骤未指定新参数时保持原默认行为；显式布尔false现在精确过滤，字符串布尔须改为JSON布尔。合法index下完整谓词零匹配进入等待的presence/absence判断，非空越界和动作索引规则不变。Step Outcome Protocol仍为`hylyre.step-outcome/1`、trace schema仍为`0.4-p0`，source-release manifest schema 2与contracts-freeze manifest schema 3保持不变。
- 使用方式、默认值和版本限制见 [常用设备操作](docs/common-device-operations.md)。软件验证与真机验收状态分开记录，未自动发布。


## 0.5.2 — Validated screenshot formats and atomic output

- Screenshot `.png`, `.jpg` and `.jpeg` output (case-insensitive) now uses the
  requested encoding and exact path, including CLI sessions and failure diagnostics.
  Unsupported or missing suffixes fail before capture/session IPC; no silent rename.
- All image consumers (CLI bytes, daemon, MCP and VLM) verify PNG/JPEG structure
  and reopen/load the complete image. Empty, forged, corrupt and truncated images
  fail instead of being labelled PNG. Valid byte response shapes remain unchanged.
  A JPEG carrying an MPF (multi-picture) segment, which Pillow reports as MPO,
  is accepted as `image/jpeg` like any other JPEG.
- Same-format output keeps original bytes; conversion keeps dimensions/content.
  JPEG quality is 95; transparent PNG pixels are composited onto white.
  Sixteen-bit grayscale PNG uses fixed 0..65535 to 0..255 scaling for JPEG,
  retaining brightness levels without per-image contrast normalization.
- Invalid input errors identify the screenshot as invalid PNG/JPEG and retain
  the original cause/exception chain; dependency and output I/O errors keep
  their existing classification.
- Image output uses a closed temporary file in the target directory and atomic
  replacement. Failed capture/validation/encoding/writing leaves no partial target
  or success reference and preserves any old valid target. The published file
  gets the mode a plain write would give (`0666` minus the process umask), not
  the owner-only mode of the temporary file. Diagnostic failure
  keeps the original business outcome and successful UI dump.
- Pillow>=11,<13 is a core runtime dependency, installed by ordinary base and
  `[device,mcp]` installs. Missing dependencies follow existing error handling
  (CLI ImportError exit 2; other screenshot errors exit 1, no success stdout).
- Version 0.5.2 uses the existing schema 2 source-release workflow. Step Outcome
  Protocol, trace schema, selectors and contract package are unchanged.
- Acceptance and installation evidence: [0.5.2 report](docs/releases/0.5.2-acceptance.md).

## 0.5.1 — `hylyre run` option ownership: no more silent ignores

Protocol, trace schema and the contract package are unchanged
(`result_protocol: hylyre.step-outcome/1`, trace schema `0.4-p0`,
`contracts_tree_sha256 = cc738c272324…`). This release is CLI-only.

- `run --plan … --on-fail skip` (and any other non-default or invalid value) was
  accepted and silently dropped: the plan path never forwarded `on_fail`, so the
  run behaved exactly like one without the flag and gave no signal. It is now a
  usage error before any device call, plan contract check or report/trace
  creation: one stderr line naming `--on-fail` and `--plan`, exit `2`, empty
  stdout. `--on-fail abort` (any case/whitespace, explicit or default) keeps
  the byte-identical behaviour of omitting the flag. The plan runner does not
  gain `on_fail` and `skip` is not implemented for plans: `blocked/prior_step`
  ledger semantics stay frozen.
- `run --help` now says what `--on-fail` means: `abort|skip` applies to
  `--steps/--steps-file` only; `--plan` accepts only the default `abort`.
- `run --steps/--steps-file … --on-fail <invalid>` is still judged by the same
  normaliser (`on_fail must be abort or skip`), but as a usage error: exit code
  `1` → `2`, and before the device agent is built or `--bundle` starts the app.
  Previously the agent was constructed first, and report mode wrapped the
  message in `verify_report failed:`.
- Every option on the shared `run` callback is registered with the execution
  paths that consume it (`plan`, `steps_report`, `steps_raw`, `subcommand`).
  One central check runs on every path and rejects any non-default value the
  path cannot consume; a value equal to the Click default passes through.
  Newly rejected instead of silently ignored: plan × `--session`/`--out`;
  steps report × `--out`/`--mock-group`/`--skip-assert-expected`; steps raw ×
  `--mock-group`/`--skip-assert-expected`/`--model-backend`.
- A callback option written before one of the 17 `run` subcommands
  (`run --on-fail skip tap …`) was accepted and dropped by the callback's early
  return. Non-default values are now a usage error there too; default-equivalent
  values (`run --on-fail abort tap …`, `run --wait-time 1.0 tap …`) still pass,
  and the options each subcommand declares itself keep binding to its handler.
- Upstream conformance test (`tests/unit/test_run_option_ownership.py`) reads
  the callback's option set and defaults from the Typer/Click command model and
  reconciles them with the ownership fixture, so an unregistered 21st option or
  a drifted default turns the suite red. Not shipped in the source release.

## 0.5.0 — Step Outcome Protocol v1 (breaking)

**Breaking**: trace schema `0.3-p0` → `0.4-p0`, and every result envelope now
declares `result_protocol: "hylyre.step-outcome/1"`. Consumers must dispatch on
`(schema_version, result_protocol)`; see [`docs/migration-0.5.md`](docs/migration-0.5.md).

The flat `StepResult` had no discriminator, so it permitted — and the verifier
actively required — contradictory rows (`blocked` carrying a `failure`,
`candidate_count=0` with a `selected_id`, `role=assertion` with a selector
failure). One real root failure was amplified into 56 downstream defects.

- `outcome` is a discriminated union: `passed` carries an observation, `failed`
  a failure, `blocked` a cause, `skipped` a reason. Nothing carries two.
- `status` is decided only by whether a step was **attempted**. `capability` and
  `infrastructure` are attribution domains: found before dispatch they block,
  found after dispatch they fail.
- A blocked suffix points at the root step with `cause.type=prior_step` and no
  longer inherits the root's failure classification.
- `selector` splits into `request` (plan intent) and `resolution` (what the
  executor found), so a requested id is never reported as a resolved one.
- `failure`/`cause`/`reason`/`resolution.reason_code` are four namespaced code
  registries; unnamespaced codes and domain/code prefix conflicts are rejected.
- A root selector/assertion failure inside a live device session must carry a
  screenshot or UI dump, with a real sha256; capture is never faked.
- `CaseResult`/`RunResult`/`tool_calls` are reduced from `steps[]` by the
  reducer shipped in the contract package, so Hylyre and its consumers cannot
  drift. `tool_calls` keeps the nested outcome shape; no flat `failure_kind`.
- **Removed**: the `status != passed → failure_kind/failure_code` rule that
  forced unexecuted and policy-skipped steps to fabricate a failure taxonomy.
- Empty cases and statically invalid steps are rejected before any device call
  with a single stdout JSON object and exit code `2`.
- Every entry (plan, fake, steps-file/batch, atomic CLI, MCP, session) builds
  rows through one builder; the offline stub no longer hand-assembles rows and
  no longer reports assertions it cannot observe.
- `run --steps-file` / `--steps` honour `--use-fakes` through the same stub
  outcome decision as the plan runner. The flag was previously accepted and
  ignored on that path, so an offline smoke test silently connected to the
  first available device; `--use-fakes` with `--session` is now refused rather
  than silently resolved.
- Contract package (`hylyre/contracts/`) ships the schema, the normative spec,
  the builder decision table, the reference reducer and 218 golden fixtures, all
  readable offline. `build_wheel.py --contracts` produces a non-installable
  contract-freeze bundle.

## 0.4.1 — structured selector identity redaction

- Preserved `by_id`, `by_key`, `id`, `key`, and `selected_id` verbatim in serialized selector evidence, including failure candidates.
- Kept user-facing text and value fields, including `expected` and `actual`, behind the existing redaction boundary.
- Kept trace schema `0.3-p0` and the existing `StepResult`/`CaseResult` field sets unchanged.

## 0.4.0 — deterministic verification and evidence

This release is intentionally behavior-tightening and is not published by this repository change.

- Added the single `CaseResult.steps[]` → trace/report evidence chain with `StepResult` roles, durations, typed failures, selector evidence, assertion evidence, and explicit `expected_check_mode`.
- Split execution, verification, and evidence verdicts; action-only cases are `completed/inconclusive` and all-skipped runs are not successful.
- Corrected Hypium wait return-value handling and Toast listener/boolean handling; unsupported capability is separate from an assertion mismatch.
- Unified selector `exact`/`contains` semantics, rejected invalid modes, made action ambiguity fail closed, and removed native/first-hit/coordinate-estimation fallbacks.
- Added deterministic aggregate-rich-text fail-closed coverage and a real-fragment evidence path.
- Added strict trace/report validation and legacy `0.1-p0`/`0.2-p4` recognition.
- Hardened review cases: aborted/skipped/empty-evidence cases cannot verify, aborts retain blocked ledger rows, and runtime/harness outcomes share one projection algorithm.
- Made nested selectors and swipe/scroll containers fail closed, kept invalid match on frozen `selector_not_found`, and corrected ordinary Text/Span rich-text semantics.
- Toast plan/batch lookahead now preserves the trigger on capability skip; selector/error/notes text is redacted before trace/report output; legacy verification output is explicit.
- Added production-dispatcher conformance coverage for real plan, CLI steps-file, and MCP session-batch paths.
- Final review hardening: uncovered Toast assertions cannot verify, explicitly identified aggregate Text and nested `all[]` targets fail closed, nested match evidence follows actual execution, scoped scroll-to uses the selected container node, and blocked suffixes preserve root classification without inflating `executed`.
- Final inline contract: removed Row/ancestor heuristics that rejected normal dynamic `contains`; flattened rich text now requires host `inline_target=true` or independent fragment/semantic target data before fail-closed handling.

See [docs/migration-0.4.md](docs/migration-0.4.md) for migration details and the pending real-device checklist.
