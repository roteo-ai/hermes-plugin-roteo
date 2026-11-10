# Upstream

| | |
|---|---|
| Upstream | `NousResearch/hermes-official-plugins`, subdirectory `claude-subscription-directsdk` |
| Fork point | commit `1b9102c7c4211b9622680fe6e2b78246634cbc1d`, plugin version 0.3.4 |
| Licence | MIT, Nous Research copyright kept in LICENSE |

## What this fork changes

Every change in shared files carries a `ROTEO` comment (`grep -rn ROTEO`).

| File | Change |
|---|---|
| `roteo.py` | New. Key and endpoint resolution, the child env, error hints |
| `model_catalog.py` | Short names follow Roteo's live `/v1/models` at load (`follow_live_catalog`), pinned table as the offline baseline; `ROTEO_LIVE_CATALOG=0` skips the read. Upstream's `ALIASES` move by hand: on a merge keep the Roteo block after the tables |
| `directsdk.py` | The inherited-env path calls `roteo.apply` instead of refusing auth overrides; provider id in `CARRIER` and `base_url`; 401/402 hints on upstream errors |
| `directsdk_setup.py` | `PLUGIN_ID`; hint texts; `setup_status` reads the Roteo key; `discover_models` and `fetch_usage` return early (upstream bodies kept unreached); telemetry default off |
| `__init__.py` | Provider id and names; `get_usage_cost` returns unknown ("billed by Roteo"), upstream body kept unreached; usage title |
| `plugin.yaml`, `pyproject.toml` | Name, version, author, homepage, `requires_hermes >=0.22.0`, Roteo settings, telemetry default off |
| `conftest.py` | `PLUGIN_NAME`; `ROTEO_REMOVED` skips upstream tests of removed behaviour, with reasons; `ROTEO_LIVE_CATALOG=0` keeps the suite offline |
| `tests/` | Provider id renamed; telemetry tests expect off by default; one guard test now expects `RoteoKeyMissing`; one cost assertion; new `test_roteo.py` and `test_live_catalog.py` |
| `README.md`, `CHANGELOG.md`, `AGENTS.md`, `LICENSE` | Roteo versions; upstream engineering rules kept in AGENTS.md |
| `assets/` | Removed (upstream artwork) |
| Setting names | Upstream's `CLAUDE_SUBSCRIPTION_DIRECTSDK_COMMAND` / `_CONFIG_DIR` are `ROTEO_CLAUDE_COMMAND` / `ROTEO_CLAUDE_CONFIG_DIR` here, in code, tests and docs: rename them in every merged hunk |

Early returns (unreached upstream code) are deliberate: they keep each merge to a few lines.

## Updating from upstream

1. Get the new upstream subdirectory at the commit you want, into a scratch folder.
2. Diff it against the fork point (or the last merged commit) to see what upstream changed.
3. Apply those changes here file by file. Where a hunk touches a `ROTEO` block, keep the Roteo behaviour.
4. Run the suite (below). Compare failures with an upstream-only run on the same machine: the fork
   must add none. New upstream tests of claude.ai-only behaviour go into `ROTEO_REMOVED` with a reason.
5. Live check on a test profile: one plain turn and one tool turn, then the Roteo usage rows.
6. Bump `version` in `plugin.yaml`, `pyproject.toml` and `roteo.VERSION`, and add a CHANGELOG entry.

## Running the tests

```sh
HERMES_AGENT_REPO=<path to hermes-agent> <hermes venv python> -m pytest -q --timeout=120 -rfEs
```

On Windows with Hermes 0.22.6, upstream itself fails 16 tests (Hermes' bootstrap relaunch and the
fake Claude Code fixtures); the fork fails the same 16 (2 of them under renamed telemetry tests).
