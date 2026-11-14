# 本机 Hypium 签名定点复核

调用 `claude -p --model claude-opus-5-5 --effort high --tools Read --strict-mcp-config --output-format json`。
实际模型 claude-opus-5-5
Session 3f3f4a05-52b7-4621-91fb-2c5ca77b71e3

**结论：四项都通过，没有阻断问题，也没有和返修直接矛盾的地方。**

1. **slide**：通过。原生签名是 `slide(start, end, area=None, slide_time=DEFAULT_SLIDE_TIME)`，常量 `DEFAULT_SLIDE_TIME = 0.3`（`uidriver.py:32,641-643`），没有 speed 参数。design 第 25 行、tasks 3.2、spec 第 13 行都写的是只把 `duration` 映射到 `slide_time`、默认 0.3、预检拒绝 `speed`，三处一致。
2. **gesture**：通过。`Gesture(area=None, sampling_time=50)` 配合 `.start(pos)`、`.move_to(pos)` 就能构造逐指的连续折线（`gesture.py:162-218`）。单指调用 `inject_gesture(gesture, speed=2000)`，多指调用 `inject_multi_finger_gesture(List[Gesture], speed=2000)`（`uidriver.py:992,1368`），两者都是一次注入。design 第 30 行、tasks 4.3、spec 的两个 Scenario 与此一致。
3. **三态读取**：通过。`_attr_bool` 的实现是 `str(attrs.get(key, "")).lower() == "true"`（`hylyre/api/selector_resolve.py:112`），确实会把缺失值当成 false。计划把它限定在点击排序和祖先查找这类既有二态调用里；过滤、`get_component_property`、`set_checked` 改走共享三态读取。design 第 45–47 行、tasks 2.7、spec 第 31 行一致。
4. **fling 速度和多指 area → Rect**：通过。原生是 `fling(..., speed: str = "fast")`，取值为 FAST/NORMAL/SLOW 三档（`uidriver.py:969-983`），和计划写的「fast/normal/slow 字符串、默认 fast」一致。`two_finger_swipe` 和 `multi_finger_touch` 的 `area` 参数类型都是 `Rect`（`uidriver.py:1388,1409`），计划由适配层从唯一控件的边界构造 Rect，方向正确。另外原生 `area` 只在端点是比例坐标时才生效，计划要求端点用屏幕绝对像素并验证没有重复偏移，这一点也对得上（tasks 2.3）。

以下三点不影响通过，留给 tasks 1.1/1.2 落实就行：
- fling 的 `distance` 实际默认值是 50，但 docstring 写的是 60。记录时以签名为准。
- 用 dump 里的 bounds 构造 `Rect` 时，要核对构造参数的顺序。
- 整数像素端点经过 `_convert_gesture_pos` → `scale_to_position` 时不能被当作比例坐标缩放，尤其要看 0/1 这类边界值。这个函数的源码我这次没读到，留到 tasks 1.2 实测确认。
