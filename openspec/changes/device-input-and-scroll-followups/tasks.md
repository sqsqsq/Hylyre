## 1. input 富选择器

- [x] 1.1 `selector_ops`: `pred_from_input_block`, `resolve_input_hit`, `uses_resolver_for_input`
- [x] 1.2 `agent.py`: `_apply_input_block` 分流；`action.type=input` 整块下发
- [x] 1.3 单测：by_type/into/action 富字段；by_id 原生不回归

## 2. scroll_to 容器感知兜底

- [x] 2.1 `scroll_until_visible` bounds 过滤全树兜底
- [x] 2.2 单测：容器内已可见 swipes==0；外部同名仍滚动

## 3. 文档与发布

- [x] 3.1 agent-plan-a / agent-loop / downstream-harness F3
- [x] 3.2 bump 0.3.0 + build_wheel 元信息同步
- [x] 3.3 pytest + packaging slow + openspec validate --strict
