## ADDED Requirements

### Requirement: API preserves normal Row contains intent

The planned action API SHALL pass ordinary dynamic Text/Row `contains` selectors through the normal selector path. It SHALL rely on explicit inline-target metadata or independent fragment/semantic evidence for rich-text fail-closed behavior.

#### Scenario: Dynamic Row remains addressable

- **WHEN** a planned touch targets a substring of ordinary Text inside a clickable Row without inline-target metadata
- **THEN** the Row is tapped using the requested `contains` semantics
