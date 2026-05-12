# Design: add-api-agent

## Layering

- `hylyre/api/agent.py` imports **only** `UiDriverBase`, `MockControllerBase`, `VlmClientBase` (no `hypium` / `lyrebird` imports).
- `hylyre/wiring.py` performs lazy imports of `HypiumDriver` / `LyrebirdController` and attaches `HttpVlmClient.from_env()`.
- `hylyre/vlm/` holds `HttpVlmClient` + JSON extraction helper; depends on `httpx` (already core).

## VLM protocol

Models return **JSON objects only** (see `_schema_instruction` in `http_vlm.py`). `extract_json_object` tolerates fenced markdown.

## CLI

`hylyre ai action|query|assert` require `HYLYRE_VLM_ENDPOINT` (optional key/model). Fail fast with exit code 2 when missing.
