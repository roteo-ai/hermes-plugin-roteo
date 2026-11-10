# Claude via Roteo for Hermes Agent

Use Claude models in [Hermes Agent](https://github.com/NousResearch/hermes-agent) through
[Roteo](https://roteo.ai), with your Roteo API key. No Claude login needed.

Hermes keeps its own agent loop, tools, approvals and compaction. The plugin runs the official
Claude Code CLI on your machine as the model client, and Claude Code sends each request to Roteo
with your key.

## Requirements

- **Hermes Agent 0.22 or newer.** On an older Hermes the plugin does not load: run `hermes update`.
- **Claude Code CLI**, installed but not logged in: `npm install -g @anthropic-ai/claude-code`
- **A Roteo API key** from [app.roteo.ai](https://app.roteo.ai)

## Install

```sh
hermes plugins install roteo-ai/hermes-plugin-roteo
hermes plugins enable roteo-claude
```

Hermes notes that this is a "custom (unreviewed) source, not from the Hermes catalog". That is
expected: the plugin installs from this repository, not from Nous Research's catalog.

Add your key to the `.env` of the Hermes profile you use:

| Profile | `.env` location |
|---|---|
| default, Windows | `%LOCALAPPDATA%\hermes\.env` |
| default, macOS / Linux | `~/.hermes/.env` |
| a named profile | `<hermes home>/profiles/<name>/.env` |

```
ROTEO_API_KEY=sk_your_roteo_key
```

## Use

```sh
hermes --provider roteo-claude -m opus
```

Or make it the profile's default in its `config.yaml`:

```yaml
model:
  provider: roteo-claude
  default: sonnet
```

Pick a model with the short names `opus`, `sonnet`, `haiku` and `fable`, or a full Claude model id.
Each short name runs the newest model of its family that Roteo serves: the plugin reads Roteo's model
list when it loads, so a new model is there the day Roteo adds it, with no plugin update.

## Billing and privacy

- Every request is billed to your Roteo balance at Roteo's prices. Hermes shows the cost as `n/a`:
  your balance and each request's charge are on [app.roteo.ai](https://app.roteo.ai).
- Roteo does not store your prompts or responses, and your identity is not passed on to the model
  provider.
- Claude Code's own telemetry is **off** by default (setting `claude_code_telemetry`).
- The plugin gives Claude Code its own config folder per Hermes profile
  (`<profile>/roteo-claude/claude-config`), apart from any Claude login of yours. It never uses
  that login, even if you have one.

## Settings

| Name | Where | What |
|---|---|---|
| `ROTEO_API_KEY` | profile `.env` | **Required.** Your Roteo API key |
| `ROTEO_BASE_URL` | profile `.env` | Optional. Defaults to `https://api.roteo.ai` |
| `roteo_base_url` | plugin setting | Optional. Overrides `ROTEO_BASE_URL` |
| `claude_config_dir` | plugin setting | Optional. Claude Code's config folder for this profile |
| `claude_code_telemetry` | plugin setting | Optional, default off. Lets Claude Code send telemetry to Anthropic |
| `ROTEO_CLAUDE_COMMAND` | environment | Optional. Path to `claude` if it is not on `PATH` |

Plugin settings live under `plugins.entries.roteo-claude.settings` in the profile's `config.yaml`,
or set them with `hermes config set`.

## Troubleshooting

| You see | Do this |
|---|---|
| "No Roteo API key for this Hermes profile" | Add `ROTEO_API_KEY` to that profile's `.env` |
| "Roteo did not accept the API key" | Check the key on [app.roteo.ai](https://app.roteo.ai) |
| "Billing or credits exhausted ... Insufficient balance" | Top up on [app.roteo.ai](https://app.roteo.ai) |
| Hermes says the provider "rejected your sign-in" and suggests `auth add ... --type oauth` | That is Hermes' generic wording. The line under it (`Provider said: ...`) has the real reason |
| "Third-party agent frameworks aren't supported on Claude models" | Hermes is on its `custom` provider, often set by its setup wizard when you enter Roteo as a custom endpoint with a Claude model. Run with `--provider roteo-claude`, or set `model.provider: roteo-claude` in `config.yaml` |
| "Gateway inaccessible: gateway_elevated" | Hermes' background gateway was started as administrator, often by the installer. Open PowerShell as administrator, run `hermes gateway stop`, then start Hermes from a normal window |
| A plugin update has no effect | Hermes keeps one gateway process for all profiles: run `hermes gateway stop`, the next request starts a fresh one |
| "Fable 5.2's safeguards flagged this message" | Fable turns down cybersecurity-related requests, in every tool. Use `-m opus` or `-m sonnet` for that task |
| "Claude Code is not installed" | Install it (see Requirements) or set `ROTEO_CLAUDE_COMMAND` |

## Credits

A fork of Nous Research's
[DirectSDK plugin for Hermes](https://github.com/NousResearch/hermes-official-plugins/tree/main/claude-subscription-directsdk)
(MIT). The transport, relay and tool bridge are theirs; this fork changes who serves the model.
See [UPSTREAM.md](UPSTREAM.md) for the fork point and every change.
