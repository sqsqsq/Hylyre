# 接口核对记录（1.1 / 1.2）

核对时间：2026-11-14；本机 Hypium 6.0.7.210，Python 3.14.5。接口源码：`D:/Program Files/Python314/Lib/site-packages/hypium/action/device/uidriver.py`，OHOS实现位于同包 `uidriver/ohos/uidriver.py`，文档位于 `docs/hypium_api_6.0.7.210.md`。仅做本机接口读取，本记录不冒充设备能力成功。

## 实际签名和默认值

```text
touch(self, target: hypium.uidriver.interface.uitree.ISelector | hypium.uidriver.interface.uitree.IUiComponent | tuple, mode: str = 'normal', scroll_target: hypium.uidriver.interface.uitree.ISelector | hypium.uidriver.interface.uitree.IUiComponent = None, wait_time: float = 0.1, offset: tuple = None)
long_click(self, target: hypium.uidriver.interface.uitree.ISelector | hypium.uidriver.interface.uitree.IUiComponent | tuple, press_time: float = 2, offset=None)
drag(self, start: hypium.uidriver.interface.uitree.ISelector | tuple | hypium.uidriver.interface.uitree.IUiComponent, end: hypium.uidriver.interface.uitree.ISelector | tuple | hypium.uidriver.interface.uitree.IUiComponent, area: hypium.uidriver.interface.uitree.ISelector | hypium.uidriver.interface.uitree.IUiComponent = None, press_time: float = 1.5, drag_time: float = 1, speed: int = None)
slide(self, start: hypium.uidriver.interface.uitree.ISelector | tuple, end: hypium.uidriver.interface.uitree.ISelector | tuple, area: hypium.uidriver.interface.uitree.ISelector | hypium.uidriver.interface.uitree.IUiComponent = None, slide_time: float = 0.3)
fling(self, direction: str, distance: int = 50, area: hypium.uidriver.interface.uitree.ISelector | hypium.uidriver.interface.uitree.IUiComponent = None, speed: str = 'fast')
pinch_in(self, area: hypium.uidriver.interface.uitree.ISelector | hypium.uidriver.interface.uitree.IUiComponent | hypium.model.basic_data_type.Rect, scale: float = 0.4, direction: str = 'diagonal', **kwargs)
pinch_out(self, area: hypium.uidriver.interface.uitree.ISelector | hypium.uidriver.interface.uitree.IUiComponent | hypium.model.basic_data_type.Rect, scale: float = 1.6, direction: str = 'diagonal', **kwargs)
two_finger_swipe(self, start1: tuple, end1: tuple, start2: tuple, end2: tuple, duration: float = 0.5, area: hypium.model.basic_data_type.Rect = None)
multi_finger_touch(self, points: List[tuple], duration: float = 0.1, area: hypium.model.basic_data_type.Rect = None)
inject_gesture(self, gesture: hypium.uidriver.gesture.Gesture, speed: int = 2000)
inject_multi_finger_gesture(self, gestures: List[hypium.uidriver.gesture.Gesture], speed: int = 2000)
press_key(self, key_code: hypium.model.basic_data_type.KeyCode | int, key_code2: hypium.model.basic_data_type.KeyCode | int = None, mode='normal')
press_combination_key(self, key1: hypium.model.basic_data_type.KeyCode | int, key2: hypium.model.basic_data_type.KeyCode | int, key3: hypium.model.basic_data_type.KeyCode | int = None)
get_component_property(self, component: hypium.uidriver.interface.uitree.ISelector | hypium.uidriver.interface.uitree.IUiComponent, property_name: str) -> Any
clear_text(self, component: hypium.uidriver.interface.uitree.ISelector | hypium.uidriver.interface.uitree.IUiComponent)
move_cursor(self, direction: str, times: int = 1)
current_app(self) -> (<class 'str'>, <class 'str'>)
has_app(self, package_name: str) -> bool
swipe_to_recent_task(self)
Gesture(area: hypium.model.basic_data_type.Rect = None, sampling_time=50)
Rect(left: int | float = 0, right: int | float = 0, top: int | float = 0, bottom: int | float = 0, display_id: int | float = -1)
```

## 适配事实与限制

- `UiParam.UP/DOWN/LEFT/RIGHT` 的实际值分别是字符串 `UP/DOWN/LEFT/RIGHT`。fling对外与swipe一致不区分大小写，适配层统一大写；映射已由四方向单测覆盖。光标左右上下也转大写，begin/end保持原生小写。
- long固定用long_click传press_time（默认2），在适配层另行保留wait_time；double/normal用touch(mode)。
- drag显式press_time要求设备API >=20且能核实；本机OHOS `_slide` 仅对press_time>1.5使用dragBetween，低于1.5会静默退化为默认按住。因此该SDK无法兑现显式<1.5，适配层明确blocked，不忽略；1.5默认和>1.5实际下传。slide duration只映射slide_time，默认0.3，不传speed。
- two_finger_swipe默认duration=0.5；multi_finger_touch默认0.1，本机原生明确最多4指，公共契约要求2–4点。
- Gesture.start(pos) 后依次move_to(pos)，无中间抬手；单指inject_gesture一次，多指inject_multi_finger_gesture一次。外层默认speed=2000，通用Gesture/PointerMatrix源码没有声明指数量上限，未猜测固定上限；至少一指、每指至少两点，具体设备不支持诚实报告。
- `utils.scale_to_position`（utils/utils.py:470）对整数也加Rect.left/top，只有float[-1,1]走比例。端点先验证屏幕绝对整数像素，再在有区域的两种多指操作中减一次区域原点后传Rect；0/1仍为整数，映射单测覆盖。
- 首批属性id/text/key/type/enabled/focused/clickable/scrollable/checked/checkable与本机原生清单一致；读取保留空字符串/null/非布尔类型，布尔只接受真实bool及字符串true/false归一，缺失/未知为不可观测。
- 原生控件映射复用dump解析身份（id/key/type及bounds），用find_all_components筛选相同bounds唯一原生组件；无法唯一对应不回落首个，不把坐标当属性控件。
- 本机原生has_app把bundle插入shell且使用子串匹配，因此统一改用固定bm dump -a并逐行全等比较，前缀相同但未安装有单测。
- 最近任务调用swipe_to_recent_task，设备须支持手势导航；current_app无bundle时blocked，ability缺失显式null及说明。

## KeyCode 符号名

以下来自本机 `KeyCode.__members__`，在公共预检冻结，无需安装device extra即可拒绝未知符号；适配层再转换原生枚举。整数键码不猜符号。

```text
FN, UNKNOWN, HOME, BACK, MEDIA_PLAY_PAUSE, MEDIA_STOP, MEDIA_NEXT, MEDIA_PREVIOUS, MEDIA_REWIND, MEDIA_FAST_FORWARD, VOLUME_UP, VOLUME_DOWN, POWER, CAMERA, VOLUME_MUTE, MUTE, BRIGHTNESS_UP, BRIGHTNESS_DOWN, NUM_0, NUM_1, NUM_2, NUM_3, NUM_4, NUM_5, NUM_6, NUM_7, NUM_8, NUM_9, STAR, POUND, DPAD_UP, DPAD_DOWN, DPAD_LEFT, DPAD_RIGHT, DPAD_CENTER, A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z, COMMA, PERIOD, ALT_LEFT, ALT_RIGHT, SHIFT_LEFT, SHIFT_RIGHT, TAB, SPACE, SYM, EXPLORER, ENVELOPE, ENTER, DEL, GRAVE, MINUS, EQUALS, LEFT_BRACKET, RIGHT_BRACKET, BACKSLASH, SEMICOLON, APOSTROPHE, SLASH, AT, PLUS, MENU, PAGE_UP, PAGE_DOWN, ESCAPE, FORWARD_DEL, CTRL_LEFT, CTRL_RIGHT, CAPS_LOCK, SCROLL_LOCK, META_LEFT, META_RIGHT, FUNCTION, SYSRQ, BREAK, MOVE_HOME, MOVE_END, INSERT, FORWARD, MEDIA_PLAY, MEDIA_PAUSE, MEDIA_CLOSE, MEDIA_EJECT, MEDIA_RECORD, F1, F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12, NUM_LOCK, NUMPAD_0, NUMPAD_1, NUMPAD_2, NUMPAD_3, NUMPAD_4, NUMPAD_5, NUMPAD_6, NUMPAD_7, NUMPAD_8, NUMPAD_9, NUMPAD_DIVIDE, NUMPAD_MULTIPLY, NUMPAD_SUBTRACT, NUMPAD_ADD, NUMPAD_DOT, NUMPAD_COMMA, NUMPAD_ENTER, NUMPAD_EQUALS, NUMPAD_LEFT_PAREN, NUMPAD_RIGHT_PAREN, VIRTUAL_MULTITASK, SLEEP, ZENKAKU_HANKAKU, ND, RO, KATAKANA, HIRAGANA, HENKAN, KATAKANA_HIRAGANA, MUHENKAN, LINEFEED, MACRO, NUMPAD_PLUSMINUS, SCALE, HANGUEL, HANJA, YEN, STOP, AGAIN, PROPS, UNDO, COPY, OPEN, PASTE, FIND, CUT, HELP, CALC, FILE, BOOKMARKS, NEXT, PLAYPAUSE, PREVIOUS, STOPCD, CONFIG, REFRESH, EXIT, EDIT, SCROLLUP, SCROLLDOWN, NEW, REDO, CLOSE, PLAY, BASSBOOST, PRINT, CHAT, FINANCE, CANCEL, KBDILLUM_TOGGLE, KBDILLUM_DOWN, KBDILLUM_UP, SEND, REPLY, FORWARDMAIL, SAVE, DOCUMENTS, VIDEO_NEXT, VIDEO_PREV, BRIGHTNESS_CYCLE, BRIGHTNESS_ZERO, DISPLAY_OFF, BTN_MISC, GOTO, INFO, PROGRAM, PVR, SUBTITLE, FULL_SCREEN, KEYBOARD, ASPECT_RATIO, PC, TV, TV2, VCR, VCR2, SAT, CD, TAPE, TUNER, PLAYER, DVD, AUDIO, VIDEO, MEMO, CALENDAR, RED, GREEN, YELLOW, BLUE, CHANNELUP, CHANNELDOWN, LAST, RESTART, SLOW, SHUFFLE, VIDEOPHONE, GAMES, ZOOMIN, ZOOMOUT, ZOOMRESET, WORDPROCESSOR, EDITOR, SPREADSHEET, GRAPHICSEDITOR, PRESENTATION, DATABASE, NEWS, VOICEMAIL, ADDRESSBOOK, MESSENGER, BRIGHTNESS_TOGGLE, SPELLCHECK, COFFEE, MEDIA_REPEAT, IMAGES, BUTTONCONFIG, TASKMANAGER, JOURNAL, CONTROLPANEL, APPSELECT, SCREENSAVER, ASSISTANT, KBD_LAYOUT_NEXT, BRIGHTNESS_MIN, BRIGHTNESS_MAX, KBDINPUTASSIST_PREV, KBDINPUTASSIST_NEXT, KBDINPUTASSIST_PREVGROUP, KBDINPUTASSIST_NEXTGROUP, KBDINPUTASSIST_ACCEPT, KBDINPUTASSIST_CANCEL, FRONT, SETUP, WAKE_UP, SENDFILE, DELETEFILE, XFER, PROG1, PROG2, MSDOS, SCREENLOCK, DIRECTION_ROTATE_DISPLAY, CYCLEWINDOWS, COMPUTER, EJECTCLOSECD, ISO, MOVE, F13, F14, F15, F16, F17, F18, F19, F20, F21, F22, F23, F24, PROG3, PROG4, DASHBOARD, SUSPEND, HP, SOUND, QUESTION, CONNECT, SPORT, SHOP, ALTERASE, SWITCHVIDEOMODE, BATTERY, BLUETOOTH, WLAN, UWB, WWAN_WIMAX, RFKILL, CHANNEL, BTN_0, BTN_1, BTN_2, BTN_3, BTN_4, BTN_5, BTN_6, BTN_7, BTN_8, BTN_9
```

## 现有链路复用位置

- `api/selector_resolve.py`、`selector_ops.py`：富选择器、唯一性、区域和等待；`component_properties.py`：共享三态布尔。
- `api/planned_step_keys.py`、`step_dispatch.py`、`scenario/plan_contract.py`：注册和零设备预检；`scenario/step_text.py`：唯一切分函数。
- `api/outcome.py`、`scenario/ledger.py`、`step_builder.py`：查询/动作/断言、既有失败分类及证据；无需升级协议/schema。
- `cli/tier_a_run_commands.py`、`mcp/tier_a_tools.py`、`session/daemon.py`：已有统一JSON路由；新操作沿run_step/run_steps绑定原session设备。

Shell实际探针及真机状态由主会话记录：hdc 3.2.0d、API26，设备exit7但transport rc0，输出/设备stderr合并进stdout，故选用唯一尾标记和stderr_available=false。`hdc_cli.structured_shell`保留原始证据、远端未知状态和超时宿主回收。实际复验见 `.hylyre/verification/extend-common-device-operations/readonly-r2/`，不能以接口签名代替手势/控件真机成功。

## Claude 首审返修核对（2026-11-14）

- OHOS实现 `_gen_pinch_in/_gen_pinch_out` 只支持diagonal/horizontal；已收紧共享预检、帮助示例、文档和入口fixture，vertical在连接前拒绝。
- `press_combination_key` 的外层和OHOS实现docstring明确“HMOS不支持三键组合，第三个按键不会生效”；OHOS实现把三键交给 `ArkUiDriver.triggerCombineKeys`。`UiDriver.get_os_type()` 在此实现总返回ohos，不能区分HMOS。三键因此核实backend.get_os_info()（底层读固定 `param get const.product.software.version`）；仅实际系统标识为OpenHarmony时调用一次原生三键，HarmonyOS/HMOS/未知全部blocked，不静默少执行一个键；两键保持原路径。当前支持设备三键正例仍属真机待验项。
- 数据操作使用同一resolver的匹配节点模式，禁用点击升父/合成inline目标；等待仅在含checked/checkable/focused（含嵌套）时使用匹配节点，其它旧rich等待与点击默认模式不变。合成dump根容器无控件身份且布尔占位为空时不作为控件候选，真实控件缺属性仍能力失败。
