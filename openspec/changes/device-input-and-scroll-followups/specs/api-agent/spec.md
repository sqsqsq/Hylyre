## ADDED Requirements

### Requirement: input rich selector and into

The system SHALL resolve `input` steps with `by_type`, `by_key`, rich selector fields, or `into` via `resolve_targets`, touch the hit center to focus, then call `input_text` on the current cursor. Plain `by_text` or `by_id` without rich fields SHALL continue using native Hypium `input_text`. `action.type=input` SHALL pass the full block (minus `type`) to the same path as root `input`.

#### Scenario: TextInput by_type with scope

- **WHEN** `{"input":{"by_type":"TextInput","scope":"top_overlay","text":"123456"}}` is executed
- **THEN** the agent touches the resolved center then inputs text without native by_text/by_id selectors

#### Scenario: into one-step syntax

- **WHEN** `{"input":{"into":{"by_type":"TextInput"},"text":"x"}}` is executed
- **THEN** focus uses `into` as the predicate and text is entered at the cursor
