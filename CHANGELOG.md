# Changelog

## [0.2.0] - 2026-11-10

### Added
- The short names `opus`, `sonnet`, `haiku` and `fable` follow Roteo's live model list: at load the
  plugin reads `<base>/v1/models` once (2 s at most, no key sent) and points each name at the newest
  model of its family, pinned at the window Roteo reports. A new model reaches Hermes the day Roteo
  adds it, with no plugin release. Offline or on any error the pinned table below applies;
  `ROTEO_LIVE_CATALOG=0` skips the read. `tests/test_live_catalog.py`.
- Claude Fable 5.2 (`claude-fable-5-2`, 1M) in the pinned table.

### Changed
- `fable` runs Claude Fable 5.2 (was 5.1). `claude-fable-5-1` stays selectable by its full id.

## [0.1.0] - Unreleased

First release of the Roteo fork, from upstream `claude-subscription-directsdk` 0.3.4
(`NousResearch/hermes-official-plugins@1b9102c7`). Upstream history: their CHANGELOG.

### Added
- `roteo.py`: Claude Code runs against Roteo with the profile's `ROTEO_API_KEY`; optional
  `ROTEO_BASE_URL` / `roteo_base_url`. Every request carries `X-Roteo-Client: hermes-roteo/<version>`.
- A per-profile Claude Code config folder (`<profile>/roteo-claude/claude-config`).
- Error hints for a rejected key (401) and a low balance (402).
- `tests/test_roteo.py`.

### Changed
- Provider id `roteo-claude`, display name "Claude via Roteo".
- Setting names `ROTEO_CLAUDE_COMMAND` and `ROTEO_CLAUDE_CONFIG_DIR` (upstream: `CLAUDE_SUBSCRIPTION_DIRECTSDK_*`).
- Requires Hermes 0.22 or newer.
- Claude Code telemetry and feature flags default to off.
- Setup readiness means "Claude Code installed and `ROTEO_API_KEY` set".
- Cost shows as `n/a` (billed by Roteo) instead of Anthropic list price.

### Removed
- The claude.ai login path, the "refuses conflicting overrides" guard, account picker discovery
  from api.anthropic.com, and Claude plan limits in `/usage`.
