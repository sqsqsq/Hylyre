# Common device operations — fixed device acceptance

Status: the fixed real-device matrix is complete on the supported contexts below. Multi-finger endpoint positives require the fixture's temporary standard Fullscreen API context on this browser; ordinary browser UI retains the measured 52 CSS-pixel second-finger UP deviation. No operation is marked passed solely because a native API returned without an exception. All test-created live resources have been cleaned up.

## Environment and raw evidence

Raw traces, UI dumps, screenshots, event streams and verification logs are retained only on the acceptance workstation under `.hylyre/verification/extend-common-device-operations/`. Git ignores this directory. Evidence paths below refer to local files. A clean checkout includes the result matrix, measured coordinates and replay scripts.

- Device: `3UJ0225321000395` (exclusive to this acceptance run).
- System: `OpenHarmony-7.0.0.111`; API level `26`; HDC `3.2.0d`.
- Hypium: `6.0.7.210`; device uitest `7.0.0.1`, agent `1.2.2`.
- Initial UI: lock screen, `com.ohos.sceneboard`; `.hylyre/verification/extend-common-device-operations/initial-ui.json`.
- Existing available apps reported by preflight: `com.huawei.hmos.browser`, `com.example.simulatedwallet`.
- Raw probes: `.hylyre/verification/extend-common-device-operations/hdc-probe.json` includes exact argv, original bytes as base64, decoded channels, transport code and timeout.

Probe command:

```powershell
python openspec/changes/archive/2026-11-14-extend-common-device-operations/acceptance/hdc_probe.py --serial 3UJ0225321000395 --out .hylyre/verification/extend-common-device-operations/hdc-probe.json
```

Observed channel contract: device `printf OUT` and device stderr `printf ERR >&2` both arrive in host stdout (`OUT\r\nERR\r\n`); host stderr is empty. Direct `exit 7` returns HDC transport code 0 and no device code. A device subshell followed by a unique outer marker returns the real code 7. Therefore structured Shell must use the unique tail marker, expose `stderr_available=false, stderr=null`, retain merged text in stdout, and separate transport/device codes. A 0.25 s host timeout of a 2 s harmless sleep yields partial `BEFORE\r\n`; `subprocess.run` kills/waits its host child. The remote process state is unknown and must remain unknown in the result. No automatic retry is justified.

## Fixed page and safety boundary

`device_fixture.py` serves one self-contained HTML page and stores only its own test events. It binds `127.0.0.1:18765`, has no external requests, writes no device file and changes no device/system setting. The service is temporary; event data stays under `.hylyre/verification/extend-common-device-operations/`.

```powershell
python openspec/changes/archive/2026-11-14-extend-common-device-operations/acceptance/device_fixture.py --events .hylyre/verification/extend-common-device-operations/fixture-events.jsonl
hdc -t 3UJ0225321000395 rport tcp:18765 tcp:18765
```

Preparation evidence: local GET returned 200; POST and `/state` round trip passed; `hdc fport ls` showed `tcp:18765 tcp:18765 [Reverse]` on the selected device. The fixture has separate `?view=gestures`, `?view=scroll`, `?view=edit` contexts. Coordinates must be read from the live dump and browser viewport before the fixed run, and remain absolute screen pixels in Hylyre JSON.

The operator unlocked the test phone and opened the fixture in Huawei Browser. The interactive results below use the phone’s page events and native UI anchors.

## Frozen matrix

Each row has one positive device context and one negative contract/stub check. Unit tests supplied the negative cases for invalid parameters and unsupported capabilities. Application queries and Shell use the same selected device context.

| Operation | Fixed positive case and independent observation | Negative case | Device status |
| --- | --- | --- | --- |
| touch | Gestures pad, `mode=double`; two stationary contacts within double-tap gap and `double-tap` event | Unknown mode rejects before injection | Passed: `interactive/touch-double`; custom 3-second long boundary also passed |
| drag | Orange box to a second point; position changes, single continuous path and press/move timing | Explicit `speed` plus `drag_time` rejects | Passed: `interactive-r3/drag`, explicit press_time=2; box moved and UP matched |
| slide | One point across pad; a single contact with expected A/B endpoints | `speed` rejects | Passed: `interactive/slide` |
| fling | Scroll view list; release samples at 0/200/600 ms show additional scroll after release | Numeric speed rejects | Passed: `interactive/fling`, actual post-release inertia observed |
| pinch_in | Gestures pad; two simultaneous contacts and measured distance ratio below 1 | Scale 1 rejects | Passed: `interactive/pinch-in` |
| pinch_out | Gestures pad; two simultaneous contacts and measured distance ratio above 1 | Scale 2 rejects | Passed: `interactive/pinch-out` |
| two_finger_swipe | Pad; two simultaneous contact paths, each start/end agrees with requested absolute coordinates | Missing end2 rejects before injection | Passed in supported fullscreen context: `interactive-fullscreen/two-finger-swipe`; ordinary UI limitation retained below |
| multi_finger_touch | Pad; at least two simultaneous stationary contacts | One point rejects | Passed in supported fullscreen context: `interactive-fullscreen/multi-finger-touch` |
| gesture | Pad single-finger bent path; one contact from start through intermediate point to end | One point in a finger rejects | Single passed: `interactive/gesture-single`; multi boundary passed: `interactive-fullscreen/gesture-multi` |
| press_key | Edit multiline: Enter yields key event and inserts newline at known cursor | Unknown KeyCode name rejects | Passed: `interactive/press-key`, actual newline and Enter event |
| press_combination_key | Edit text: CTRL+A selection covers entire fixture text | Fewer than two keys rejects | Passed: `interactive-r2/combination`, selectionStart=0/end=4 for ABCD |
| get_component_property | Edit fixture checkbox: read `checked` and independently compare DOM change event/display | Unsupported property rejects | Passed after repair: `interactive-r2/get-property`, trace value is real false, DOM false, target text remains redacted |
| shell | Device fixed stdout and actual device exit code | Empty command rejects | Real success/nonzero/special/timeout verified; transport-error stub remains developer evidence |
| clear_text | Edit fixture text initially ABCD; native clear leaves observable empty string | Non-input target fails | Passed: `interactive/clear-text` |
| move_cursor | Edit fixture text ABCD, move begin/right twice, input X; observed text becomes ABXCD | `times=0` rejects | Passed: `interactive/move-cursor` |
| wait_for | Edit checkbox exists with `checked=false`, then with `checked=true` after set | Checked predicate mismatch fails assertion (unit stub) | Passed: `interactive-r2/wait-for`; true is also proved by indexed regression |
| wait_gone | Edit checkbox checked=true: no `checked=false` match; target remains separately observable | Missing checked observation must not yield false positive (unit stub) | Passed without redundant index in `interactive-r3/wait-gone`; original index=0 failure also passed after production repair in `wait-gone-index-regression/original-index` |
| set_checked | Edit checkbox false→true: exactly one change; repeat true: no extra change (`changed=false`) | Not-checkable button; readback failure stub | Passed: `interactive-r2/set-checked`, changed true then false and DOM changes=1; real non-checkable negative passed in `not-checkable` |
| current_app | Fixed page foreground is Huawei Browser; independently compare dump bundle | Unsupported driver stub reports capability | Passed: `interactive-r2/current-app`, bundle=com.huawei.hmos.browser; locked unobservable negative retained |
| has_app | Huawei Browser installed=true; fixed non-existing `com.hylyre.acceptance.notinstalled` installed=false | Empty bundle rejects | Both true/false real values verified |
| recent_tasks | Enter actual recent-tasks UI; dump/screenshot shows task switcher | Unsupported driver stub reports capability | Real passed from unlocked desktop; task switcher screenshot inspected; Back restored desktop; report verifies |

Only the design's explicit extra boundaries were added: `touch mode=long, press_time=3` produced the stationary approximately 3-second contact and Long press menu; single/multi continuous-path shapes and both pinch directions passed; set_checked's unchanged/switch/not-checkable reuse the real row, with readback-failure stub evidence; has_app installed/uninstalled reuse its row. Shell normal/nonzero/special/timeout passed on the device and transport error is stub evidence. Default normal tap reuses the implementation's existing regression evidence, with no extra touch matrix row. Negative parameter/capability evidence is in the implementation's `tests/unit/test_common_device_operations.py` (invalid-before-connect, missing attribute wait, idempotence/readback failure, endpoint bounds, optional-driver capability) and `tests/unit/test_structured_device_shell.py` (transport/marker/timeout cases); it is not mislabeled as physical-device execution.

## Real read-only results

The first run caught HDC CRLF tail markers being rejected and an unregistered failure code causing report schema failures; both were returned to the implementation owner and rechecked. A separate lock-screen read exposed `[None, None]` being incorrectly accepted by `current_app`; the fix now returns `blocked/capability.unsupported`. Original failure artifacts remain under `readonly/` and `readonly-app/` for diagnosis; they are not the final passing run.

The final session run is `.hylyre/verification/extend-common-device-operations/readonly-r2/`. Each case has the exact `*.steps.json`, `*.command.json`, `*.report.md`, `*.trace.json`, and raw Shell log artifacts under its `failures/` directory:

| Case | Observed facts | Report verify |
| --- | --- | --- |
| shell-success | passed; stdout `hylyre:ok\r\n`; device exit 0; transport 0; marker found | Passed |
| shell-nonzero | failed; stdout `hylyre:failure\r\n`; device exit 7; transport 0; valid device-command-failed code | Passed |
| shell-special | passed; stdout `中文;分号；与 空格\r\nquote"single\r\n`; device exit 0 | Passed |
| shell-timeout | failed/transport_failure; stdout `BEFORE\r\n`; device exit null; timed_out true; remote_status_unknown true | Passed |
| has-app | two passed action observations: browser installed true; fixed missing bundle installed false | Passed |
| current-app | lock screen returned no observable bundle; blocked/capability with explicit reason | Passed |

All Shell cases truthfully expose `stderr_available=false, stderr=null`. No extra device stderr channel is claimed. Windows terminal display initially garbled Chinese in a diagnostic, but the raw UTF-8 evidence was correct; the acceptance runner now sets `PYTHONUTF8=1` for CLI subprocesses.

The representative no-session run is `readonly-no-session/`: `shell-success` and `has-app` facts match the session facts exactly except for the generated artifact path; both reports verify. `readonly-plan/` is the real `--plan` execution of `shell-special-test-plan.md`: exactly two Shell steps, with string-internal ASCII/Chinese semicolons, quotes and escaped newline preserved; the inter-object Chinese semicolon splits the steps correctly. The plan/report/trace contract check passes. Existing CLI rejects `--session` with `--plan`, so this plan run uses the explicit device serial.

The six final session reports, two representative no-session reports, and one plan report all verify. Query-only cases remain `verification=inconclusive`, have action roles, and add no assertion coverage. A CLI exit 1 for a query-only report must therefore not be read as a failed query action; inspect the StepResult and verification fields above.

## Replaying the interactive cases

The fixture now emits a visible-page heartbeat with viewport, element rectangles, test-only values, selection and focused element. Its status area has fixed height so telemetry cannot move the gesture pad during a run. The live runner requires both a fresh page heartbeat and matching reset/nav anchors in the actual native dump before any coordinate action. It derives screen-pixel coordinates from those anchors; native component operations additionally require a real unique dump node matching the fixture rectangle. A DOM point is never substituted for a readable native component.

```powershell
python openspec/changes/archive/2026-11-14-extend-common-device-operations/acceptance/run_interactive_acceptance.py --self-check
python openspec/changes/archive/2026-11-14-extend-common-device-operations/acceptance/run_interactive_acceptance.py --wait 3600 --fullscreen-multitouch
```

The offline self-check validates every generated payload and tests positive/negative path oracles without device actions. The second command waits for the manually opened page, then runs the remaining fixed cases without more prompts. It saves dynamic `*.steps.json`, before dumps, command logs, report/trace, event slices, and `interactive/summary.json`. Each generated report is verified. Gesture oracles compare simultaneous contact count, continuous paths and actual endpoints/intermediate points; state/edit oracles use fixture values/events independent from Hylyre outcomes. Missing native observability remains incomplete. Recent-tasks saves after-action dump/screenshot, returns with Back, and stays `needs_visual_review` until the actual screenshot is inspected. `--only <case-name>` supports narrow reruns after a real defect; it does not broaden the matrix.

## Device preparation history

At 08:54 UTC the phone was confirmed unlocked to its launcher (`phone-current.ui.json/png`). The first HTTP page events were from **Windows Chrome**, not the phone; the watcher had injected no actions because the native anchors did not match. Event-source isolation now requires a mobile/Harmony user agent, a per-page `clientId`, fresh heartbeat and matching native anchors; each oracle event slice is restricted to the current phone page's `clientId`. Old desktop events remain raw diagnostic history only.

The independent recent-tasks case then passed from the unlocked launcher: `recent-tasks-real/recent-tasks.trace.json` has a passed action; `after.ui.json` contains `RecentEmptyView` and `RecentEmptyView_text_noRecents`; visually inspected `after.png` shows “最近无运行应用”. The report verifies, and `restored.ui.json` confirms Back restored the launcher. The remaining interactive cases ran after the phone browser opened the fixture.

## Execution and completion conditions

Use real `python -m hylyre run ...` or the shared HylyreAgent/session entry; save exact steps, command output, trace/report, before/after dump and event slices. The ephemeral acceptance session used `.hylyre/verification/extend-common-device-operations/session.json` and was stopped/deleted during cleanup. Query observations are actions and do not count as assertions. A supported-operation success needs the matching page event/property change, not just an executed step.

For every generated report/trace:

```powershell
python -m hylyre report verify --report <report.md> --trace <trace.json>
```

## Final interactive result and browser limitation

The actual phone page was identified by `Phone; OpenHarmony 7.0; Android 10`, `ArkWeb/7.0.0.111 Mobile HuaweiBrowser/6.1.9.351`, viewport width 440 CSS pixels and DPR 3, plus matching live native reset/nav anchors. Windows desktop Chrome events were excluded by user agent and per-page client ID. Every accepted interactive report has its own command log, `*.steps.json`, `*.events.json`, `*.trace.json`, `*.report.md`, and a successful `*-verify.command.json` under the directory listed in the matrix.

Two real production defects were found and closed by the implementation owner during interactive acceptance: boolean property `value=false` was incorrectly redacted, and `wait_gone` with `index=0` could treat zero matches as a selector error. After new sessions loaded the repairs, `interactive-r2/get-property` preserves a JSON boolean false while target text remains redacted, and the **original unchanged** indexed steps pass in `wait-gone-index-regression/original-index`. The latter has touch → absence checked=false → presence checked=true all passed, independent DOM checked=true with one change, and report verify passed. The index-free `interactive-r3/wait-gone` is a second passing control.

The fixed page/harness was also corrected: keyboard scrolling could move the reset control offscreen, so the header is sticky, reset blurs and scrolls only the fixture, and setup dismisses a visible keyboard. Drag's original 0.8-second requested hold was correctly blocked by the documented SDK minimum; the supported 2-second case passed in R3, with a 2765 ms continuous contact, roughly 2 seconds before movement, and the orange box moving from (30,80) to (259,172). Both MOVE and UP match its requested endpoint.

Ordinary Huawei Browser UI has a repeatable second-finger **UP-coordinate deviation**, even while DOWN, MOVE, element bounds and viewport values remain stable. Both `touchend` and `pointerup` report the deviation; event `screenY` aliases `clientY` here, so it is not an independent physical-coordinate channel. The native PointerMatrix diagnostic from the implementation owner contains the intended endpoints. These facts do not identify the exact internal layer responsible; no coordinate compensation was added to production or the fixture.

The standard, user-gesture-triggered `requestFullscreen({navigationUI:'hide'})` context supplies complete supported-device positives for all three affected forms. The device emitted `fullscreen=true`, viewport 440×667/DPR3, and `cleanup/fullscreen.png` visually confirms browser chrome is absent. With the same operation shapes and endpoint checks, all DOWN/MOVE/UP values agree. `interactive-fullscreen/summary.json` reports three passed cases, each with `end_coordinate_verified=true` and report verification passed. Native/DOM Y calibration changed from about 272.5 to 118.5 screen pixels; the approximately 154-pixel change is close to the ordinary-mode 156-pixel/52-CSS-pixel deviation. This is evidence that the browser UI context matters, not proof of a specific internal conversion bug.

Observed coordinates below are CSS client coordinates from raw phone events. The requested absolute screen-pixel endpoints remain in each `*.steps.json`; DOWN/MOVE/UP are kept separate. Each pair is finger 1 / finger 2.

| Context / operation | DOWN | Last MOVE | UP | Conclusion |
| --- | --- | --- | --- | --- |
| Ordinary / two-finger swipe | (137,253) / (303,253) | (137,372) / (303,372) | (137,372) / (303,424) | Execution/overlap/path passed; second UP +52, endpoint not fully verified |
| Ordinary / multi-touch | (137,283) / (303,283) | Same as DOWN; no MOVE | (137,283) / (303,335) | Two simultaneous contacts held 426 ms; second UP +52 |
| Ordinary / multi gesture | (95,253) / (262,253) | (176,254) / (342,254) | (176,254) / (342,306) | Continuous bent paths correct; second UP +52 |
| Fullscreen / two-finger swipe | (137,260) / (303,260) | (137,388) / (303,388) | (137,388) / (303,388) | Fully passed |
| Fullscreen / multi-touch | (137,293) / (303,293) | Same as DOWN; no MOVE | (137,293) / (303,293) | Fully passed; simultaneous hold 432 ms |
| Fullscreen / multi gesture | (95,260) / (262,260) | (177,260) / (343,260) | (177,260) / (343,260) | Fully passed; continuous paths and intermediate points matched |

Replay uses `--fullscreen-multitouch` to enter the supported context with an actual fixture button tap; it exits owned fullscreen at the end. Running without that flag intentionally retains ordinary-browser diagnostics and may produce `partial_end_unverified`. The original ordinary-mode deviation is not relabeled as success. Default tap compatibility, parameter negatives, missing capability and difficult readback/transport failures reuse the implementation's unit/stub evidence; they are not expanded into another physical-device Cartesian product.

Cleanup is complete, with evidence in `cleanup/`: fullscreen explicitly exited (`fullscreen=false`); only the identified “Hylyre device fixture” tab was closed; Home restored `com.ohos.sceneboard`; the acceptance daemon stopped and session file disappeared; the fixture/waiter process count and loopback port 18765 listener count are zero; the exact `tcp:18765 tcp:18765` reverse task was removed. The previously present `tcp:9912 localabstract:uitest_socket` task was left unchanged. No system setting or user application data was modified.
