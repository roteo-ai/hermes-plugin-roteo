"""Test bootstrap and shared fixture.

The standalone plugin imports Hermes core (`providers`, `agent`) from a checkout: set
``HERMES_AGENT_REPO`` to your hermes-agent clone (default ``~/.hermes/hermes-agent``).

``profile`` loads this repo exactly as `hermes plugins install` leaves it —
``$HERMES_HOME/plugins/<name>/`` with ``kind: model-provider`` — through core's provider discovery.
"""
import os
import shutil
import sys
from pathlib import Path

import pytest

# ROTEO: model_catalog reads Roteo's live model list at import; the suite stays offline and checks the
# pinned tables (tests/test_live_catalog.py drives the live path with fakes).
os.environ.setdefault("ROTEO_LIVE_CATALOG", "0")

HERMES_AGENT_REPO = Path(os.environ.get("HERMES_AGENT_REPO") or Path.home() / ".hermes" / "hermes-agent").expanduser()
REPO_ROOT = Path(__file__).resolve().parent
PLUGIN_NAME = "roteo-claude"
for path in (str(HERMES_AGENT_REPO), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

collect_ignore = ["__init__.py", "directsdk.py", "directsdk_setup.py", "admission.py", "model_catalog.py",
                  "inert_mcp.py", "evals"]

# ROTEO: upstream tests of behaviour this fork removes on purpose (UPSTREAM.md). Skipped rather than deleted,
# so upstream merges stay small and this list shows exactly what was dropped. Key: file or node id, no params.
_NO_PLAN = "no claude.ai plan behind Roteo: no plan limits or plan rules to read"
_NO_DISCOVERY = "no first-party picker discovery from api.anthropic.com: the pinned catalog is the list"
_NO_AUTH_STATUS = "readiness is the profile's ROTEO_API_KEY, not Claude Code's `auth status`"
ROTEO_REMOVED = {
    "tests/test_directsdk_account_usage.py": _NO_PLAN,
    "tests/test_directsdk_setup.py::test_fable_5_and_5_1_follow_the_documented_plan_rule": _NO_PLAN,
    "tests/test_directsdk_setup.py::test_setup_status_reports_login_and_models_from_the_cli": _NO_AUTH_STATUS,
    "tests/test_directsdk_setup.py::test_a_generic_1m_row_keeps_its_version_in_the_label": _NO_DISCOVERY,
    "tests/test_directsdk_setup.py::test_an_inherited_backend_override_keeps_discovery_behind_the_relay": _NO_DISCOVERY,
    "tests/test_directsdk_setup.py::test_every_model_the_cli_advertises_is_selectable": _NO_DISCOVERY,
    "tests/test_directsdk_setup.py::test_hermes_never_budgets_a_discovered_row_past_the_native_window": _NO_DISCOVERY,
    "tests/test_directsdk_setup.py::test_pinned_models_the_picker_omits_stay_selectable": _NO_DISCOVERY,
    "tests/test_directsdk_setup.py::test_privacy_flags_shrunk_picker_is_unioned_with_the_pinned_table": _NO_DISCOVERY,
    # Both of its probes spawn Claude Code in upstream; here neither spawns anything.
    "tests/test_directsdk_config_dir.py::test_setup_probes_pass_the_profile_directory": _NO_DISCOVERY + "; " + _NO_AUTH_STATUS,
}


def pytest_collection_modifyitems(config, items):
    for item in items:
        node = item.nodeid.replace("\\", "/").split("[")[0]
        reason = ROTEO_REMOVED.get(node) or ROTEO_REMOVED.get(node.split("::")[0])
        if reason:
            item.add_marker(pytest.mark.skip(reason="ROTEO: " + reason))


@pytest.fixture
def profile(tmp_path, monkeypatch):
    import providers

    home = tmp_path / "hermes-home"
    installed = home / "plugins" / PLUGIN_NAME
    shutil.copytree(REPO_ROOT, installed, ignore=shutil.ignore_patterns(".git", "tests", "evals", "__pycache__"))
    monkeypatch.setenv("HERMES_HOME", str(home))
    (home / "config.yaml").write_text("plugins:\n  enabled: []\n", encoding="utf-8")
    # A machine with Claude Code installed must not leak it into offline tests.
    monkeypatch.setenv("ROTEO_CLAUDE_COMMAND", str(tmp_path / "no-such-claude"))
    for name in tuple(sys.modules):
        if name.startswith("_hermes_user_provider_"):
            monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(providers, "_REGISTRY", {})
    monkeypatch.setattr(providers, "_ALIASES", {})
    monkeypatch.setattr(providers, "_PROVIDER_LIST_CACHE", None)
    monkeypatch.setattr(providers, "_discovered", False)
    providers._discover_providers()
    result = providers.get_provider_profile(PLUGIN_NAME)
    assert result is not None, "installed-plugin discovery (step 2b) did not register the provider"
    return result
