"""The Roteo layer: which key and endpoint the Claude Code child gets, and what never reaches it."""
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import roteo  # noqa: E402
import directsdk  # noqa: E402
import directsdk_setup  # noqa: E402

KEY = 'sk_test_roteo_key_0123456789abcdef'


@pytest.fixture
def home(tmp_path, monkeypatch):
    """An empty Hermes home, so no test ever reads the machine's real profile .env."""
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    for name in (roteo.KEY_ENV, roteo.URL_ENV):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def write_env(home, **values):
    (home / '.env').write_text(''.join(f'{k}={v}\n' for k, v in values.items()), encoding='utf-8')


def test_manifest_matches_the_module():
    manifest = (ROOT / 'plugin.yaml').read_text(encoding='utf-8')
    assert f'name: {roteo.PLUGIN_ID}\n' in manifest
    assert f'version: {roteo.VERSION}\n' in manifest
    assert 'requires_hermes: ">=0.22.0"' in manifest


def test_the_key_comes_from_the_profile_env(home):
    write_env(home, ROTEO_API_KEY=KEY)
    assert roteo.secret(roteo.KEY_ENV) == KEY


def test_a_quoted_or_blank_key_is_read_as_such(home):
    write_env(home, ROTEO_API_KEY=f'"{KEY}"')
    assert roteo.secret(roteo.KEY_ENV) == KEY
    write_env(home, ROTEO_API_KEY='')
    assert roteo.secret(roteo.KEY_ENV) is None


def test_apply_points_the_child_at_roteo_and_nothing_else(home):
    write_env(home, ROTEO_API_KEY=KEY)
    env = {'ANTHROPIC_API_KEY': 'sk-ant-other', 'ANTHROPIC_BASE_URL': 'https://api.anthropic.com',
           'CLAUDE_CODE_OAUTH_TOKEN': 'oauth', 'CLAUDE_CONFIG_DIR': str(home / 'users-own-claude'),
           'CLAUDE_CODE_USE_BEDROCK': '1', 'ANTHROPIC_CUSTOM_HEADERS': 'X-Other: 1', 'PATH': 'kept'}
    roteo.apply(env)
    assert env['ANTHROPIC_BASE_URL'] == roteo.DEFAULT_BASE_URL
    assert env['ANTHROPIC_AUTH_TOKEN'] == KEY
    assert env['ANTHROPIC_CUSTOM_HEADERS'] == f'{roteo.CLIENT_HEADER}: hermes-roteo/{roteo.VERSION}'
    assert Path(env['CLAUDE_CONFIG_DIR']) == home / roteo.PLUGIN_ID / 'claude-config'
    assert Path(env['CLAUDE_CONFIG_DIR']).is_dir()
    for gone in ('ANTHROPIC_API_KEY', 'CLAUDE_CODE_OAUTH_TOKEN', 'CLAUDE_CODE_USE_BEDROCK'):
        assert gone not in env
    assert env['PATH'] == 'kept'


def test_no_key_fails_before_anything_starts(home):
    env = {'ANTHROPIC_AUTH_TOKEN': 'someone-elses'}
    with pytest.raises(roteo.RoteoKeyMissing, match=roteo.KEY_ENV):
        roteo.apply(env)
    assert roteo.RoteoKeyMissing.status_code == 401


def test_the_request_path_refuses_without_a_key(home):
    with pytest.raises(roteo.RoteoKeyMissing):
        directsdk.Client(command='/does/not/exist').create(
            model='sonnet', messages=[{'role': 'user', 'content': 'hi'}])


def test_base_url_setting_env_and_default(home):
    assert roteo.base_url() == 'https://api.roteo.ai'
    write_env(home, ROTEO_BASE_URL='https://eu.roteo.example/')
    assert roteo.base_url() == 'https://eu.roteo.example'
    assert roteo.base_url('https://setting.example') == 'https://setting.example'
    assert roteo.base_url('http://127.0.0.1:3001') == 'http://127.0.0.1:3001'


def test_the_token_never_travels_in_clear_over_a_network(home):
    with pytest.raises(ValueError, match='https'):
        roteo.base_url('http://api.roteo.ai')


def test_hints_for_answers_the_user_can_act_on():
    assert roteo.KEY_ENV in roteo.upstream_hint(401)
    assert 'Top up' in roteo.upstream_hint(402)
    assert roteo.upstream_hint(500) == ''


def test_setup_reports_ready_only_with_a_key(home, monkeypatch):
    monkeypatch.setattr(directsdk_setup, '_resolve', lambda command, env: ['claude'])
    missing = directsdk_setup.setup_status()
    assert missing['available'] and not missing['logged_in'] and roteo.KEY_ENV in missing['detail']
    write_env(home, ROTEO_API_KEY=KEY)
    ready = directsdk_setup.setup_status()
    assert ready['logged_in'] and ready['plan'] == 'Roteo' and ready['login_command'] is None


def test_no_anthropic_discovery_or_plan_limits(home):
    assert directsdk_setup.discover_models() is None
    limits, reason = directsdk_setup.fetch_usage()
    assert limits is None and roteo.DASHBOARD_URL in reason


def test_telemetry_is_off_unless_turned_on(home, monkeypatch):
    monkeypatch.setattr(directsdk_setup, '_setting', lambda key, default=None: default)
    assert directsdk_setup.telemetry_enabled() is False
    monkeypatch.setattr(directsdk_setup, '_setting', lambda key, default=None: True)
    assert directsdk_setup.telemetry_enabled() is True
