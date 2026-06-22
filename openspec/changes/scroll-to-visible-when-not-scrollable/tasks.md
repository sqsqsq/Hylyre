## 1. Implementation

- [x] 1.1 `find_container_root` in collect_cmd.py
- [x] 1.2 `resolve_first_hit_match_center_in_container` in selector_resolve.py
- [x] 1.3 Refactor `scroll_until_visible` + native fallback
- [x] 1.4 `_apply_scroll_to_block` visible=True for pure by_text

## 2. Tests

- [x] 2.1 scrollable=false primary regression
- [x] 2.2 pre-lift sibling + lift-center-outside
- [x] 2.3 container=None visible + native gate + list→scroll fallback
- [x] 2.4 Existing scroll tests green

## 3. Release

- [x] 3.1 docs agent-loop / agent-plan-a
- [x] 3.2 bump 0.3.1 + pytest + openspec validate
