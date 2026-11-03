# Changelog

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
