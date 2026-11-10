## ADDED Requirements

### Requirement: Screenshot output format follows the requested path

All screenshot file outputs SHALL preserve the requested path and encode valid PNG for `.png` and valid JPEG for `.jpg` or `.jpeg`, with case-insensitive suffix recognition. Output SHALL retain the captured dimensions and visible content. Unsupported or missing suffixes SHALL fail before capture and SHALL NOT be silently renamed.

#### Scenario: JPEG and PNG are saved in either supported format
- **WHEN** a valid JPEG or PNG capture is saved to any supported suffix, including uppercase variants
- **THEN** the requested path contains a complete image in the requested format with the captured dimensions and content
- **AND** success returns that actual completed path without renaming it

#### Scenario: Unsupported output is rejected before device access
- **WHEN** the requested output has no suffix or has `.txt`, `.bmp` or another unsupported suffix
- **THEN** the operation fails with the supported formats in its diagnostic before capture or session IPC and creates no alternative output

#### Scenario: Transparent PNG is encoded as JPEG
- **WHEN** PNG pixels carry alpha or palette transparency and the requested output is JPEG
- **THEN** transparency is composited onto white before JPEG encoding without changing dimensions or discarding visible foreground content

### Requirement: File success requires a valid complete captured image

Screenshot file output SHALL reject empty, non-image, unsupported, structurally corrupt or incompletely decodable data. A matching signature alone SHALL NOT establish validity. Valid same-format inputs SHALL be preserved without re-encoding; cross-format conversion SHALL use the current capture, never a placeholder or stale file.

#### Scenario: Correct signature does not hide damaged image data
- **WHEN** an input has a forged PNG/JPEG header, a bad PNG CRC, or truncated image data
- **THEN** file output fails with a diagnostic reason and produces no successful screenshot reference

#### Scenario: Valid same-format content is preserved
- **WHEN** a complete valid JPEG is saved as JPEG or PNG as PNG
- **THEN** the saved bytes equal the validated input bytes

### Requirement: Screenshot file publication is failure safe

Screenshot saving SHALL publish the final target only after successful validation, encoding and complete temporary-file writing. Failure SHALL NOT leave a partial final target, destroy an existing valid target, return a successful path or register a successful screenshot attachment. Temporary files from a failed operation SHALL be cleaned up.

#### Scenario: New target write or replacement fails
- **WHEN** encoding, temporary writing, closing or final replacement fails and the target did not exist
- **THEN** the caller receives failure, no partial final target or successful path is exposed, and the operation's temporary file is removed

#### Scenario: Existing target survives a failed attempt
- **WHEN** a valid target exists and the new capture, validation, encoding, writing or replacement fails
- **THEN** the previous target bytes remain unchanged and the previous file is not returned or attached as the new capture

### Requirement: All screenshot file entry points share the output contract

CLI one-shot and session screenshot output and all failure-diagnostic screenshot producers SHALL apply the same image output contract. Diagnostic screenshots SHALL remain `.png` and SHALL be attached only after valid PNG publication. Capture failure SHALL preserve the original business failure and other successful diagnostic materials using existing result semantics.

#### Scenario: One-shot and session CLI outputs agree
- **WHEN** the same valid captured bytes and target suffix are supplied through the actual CLI one-shot and session paths
- **THEN** both paths produce correctly encoded output through the production writer

#### Scenario: Plan, batch and atomic failures attach real images
- **WHEN** a plan, steps batch or atomic step triggers failure capture successfully
- **THEN** its screenshot reference points to a complete PNG and its hash corresponds to the completed file

#### Scenario: Screenshot fails while UI dump succeeds
- **WHEN** failure-boundary screenshot capture or saving fails but UI dump capture succeeds
- **THEN** no screenshot attachment is registered, the UI dump remains available, and the original business failure is retained with capture diagnostics under existing error handling

### Requirement: Image validation and MIME are consistent across byte consumers

CLI screenshot bytes, session daemon, both MCP screenshot modes and VLM data URLs SHALL use shared complete JPEG/PNG structural validation and decoding before returning the actual MIME. Empty, unknown, corrupt or truncated inputs SHALL fail instead of being labelled as valid images. These paths SHALL preserve valid source bytes, standard MIME values and existing return shapes without adding file-output parameters.

#### Scenario: Supported source bytes retain truthful MIME and shape
- **WHEN** real valid JPEG or PNG bytes pass through one-shot or session screenshot transport, MCP or VLM
- **THEN** MIME is respectively `image/jpeg` or `image/png`, the decoded base64 bytes equal the source bytes, and the existing tuple, JSON or data URL shape is preserved

#### Scenario: Invalid source bytes are rejected
- **WHEN** any of these paths receives empty data, unknown signatures, a forged header, a bad PNG CRC or truncated JPEG/PNG
- **THEN** it uses its existing error mechanism rather than returning a successful image payload or data URL

### Requirement: Errors remain observable without protocol changes

CLI screenshot failures SHALL exit nonzero and report a diagnosable cause without printing a success path. Dependency ImportError SHALL retain exit code 2 and other screenshot exceptions SHALL retain exit code 1. Other entry points SHALL retain existing error envelopes and SHALL NOT change Step Outcome, trace schema, selector or step execution semantics.

#### Scenario: CLI cannot complete image processing
- **WHEN** capture, dependency loading, image validation, encoding or file publication fails
- **THEN** stderr explains the failure, exit status follows the existing mapping, and stdout contains no successful screenshot path

### Requirement: Screenshot dependencies and release are installable and verifiable

Pillow SHALL be declared as a core runtime dependency compatible with the supported Python range. The completed change SHALL be delivered as version 0.5.2 using the existing schema 2 source-release builder and verifier. Package metadata, runtime version and manifest version SHALL agree; source contents, LF normalization, sizes and hashes SHALL pass existing verification. Existing package-data SHALL be retained.

#### Scenario: Clean installation obtains image support
- **WHEN** the actual source-release copy is installed into a clean environment without dev extras
- **THEN** image-processing dependencies are resolved from package metadata and installed-package file-output checks succeed from outside the repository
- **AND** installation with the documented device/MCP extras supports the applicable entry-point checks

#### Scenario: Release verification and version agree
- **WHEN** the 0.5.2 source artifact is built and verified through existing release commands
- **THEN** verification succeeds, metadata/runtime/manifest report 0.5.2, and the final report records its source-tree fingerprint and artifact location

### Requirement: Acceptance evidence distinguishes execution environments

The delivery report SHALL map A1–A13 of the input requirement to commands, results, evidence and gaps. Image tests SHALL use genuine decodable images and execute production validation/encoding/writing, while fault cases SHALL include realistic corruption and I/O failures. Entry-point wiring SHALL be tested separately from shared-function unit tests. Offline tests SHALL NOT be reported as actual device verification.

#### Scenario: Device verification is unavailable
- **WHEN** offline image and installed-package checks complete but no compatible device is available
- **THEN** the report records actual device checks as unexecuted, states the compatibility limitation, and does not claim full acceptance or actual-device success

#### Scenario: Entry-point acceptance exercises actual output code
- **WHEN** a CLI, session, MCP or diagnostic acceptance case substitutes capture or transport at its boundary
- **THEN** production format handling and applicable output/attachment code still execute, and the result is classified as offline evidence

### Requirement: Sixteen-bit grayscale conversion retains fixed-range luminance

Valid sixteen-bit grayscale PNG input converted to JPEG SHALL map the fixed 0..65535 range linearly to 0..255 before eight-bit encoding, retaining dimensions and spatial luminance levels without per-image min/max normalization. Same-format PNG output SHALL preserve the original bytes.

#### Scenario: Grayscale values exceed the eight-bit range
- **WHEN** a valid sixteen-bit PNG contains spatial blocks at low, middle and high grayscale values
- **THEN** JPEG output preserves their distinct brightness according to the fixed full-range mapping instead of clipping all values above 255 to white
- **AND** requesting PNG preserves the validated source bytes

### Requirement: Invalid image errors preserve diagnostic context and attribution

Image recognition, structural verification and decoding failures SHALL identify the screenshot as invalid PNG/JPEG and retain the original cause and exception chain. Dependency ImportError SHALL retain existing handling, and output encoding or I/O failures SHALL NOT be relabelled as invalid input.

#### Scenario: Invalid capture reaches the CLI or failure diagnostics
- **WHEN** invalid image bytes fail recognition, verification or loading
- **THEN** CLI stderr identifies the invalid PNG/JPEG screenshot and includes the underlying cause, without success stdout
- **AND** failure capture preserves the original business failure and successful UI dump
