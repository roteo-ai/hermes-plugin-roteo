"""Roteo wiring for the Claude Code child: where it sends requests, and with which key.

Hermes drives the official Claude Code CLI; Roteo (https://roteo.ai) serves the model. The child talks
to Roteo's Anthropic-compatible endpoint with the profile's ``ROTEO_API_KEY`` as its bearer token,
through the plugin's loopback relay (admission.py). It never falls back to a claude.ai login or to
api.anthropic.com: without a key the request fails before Claude Code starts.
"""
import os
from pathlib import Path

PLUGIN_ID = 'roteo-claude'
VERSION = '0.1.0'  # plugin.yaml `version`; tests/test_roteo.py keeps them equal
KEY_ENV = 'ROTEO_API_KEY'
URL_ENV = 'ROTEO_BASE_URL'
DEFAULT_BASE_URL = 'https://api.roteo.ai'
BASE_URL_SETTING = 'roteo_base_url'
# Roteo logs it to tell this traffic apart; the gateway does not forward it upstream.
CLIENT_HEADER = 'X-Roteo-Client'
DASHBOARD_URL = 'https://app.roteo.ai'

KEY_HINT = (f'No Roteo API key for this Hermes profile. Add {KEY_ENV}=sk_... to the profile .env '
            f'(create a key at {DASHBOARD_URL}), then try again.')
REJECTED_KEY_HINT = f'Roteo did not accept the API key. Check {KEY_ENV} in the profile .env ({DASHBOARD_URL}).'
BALANCE_HINT = f'Your Roteo balance is too low for this request. Top up at {DASHBOARD_URL}.'

# Nothing else may authenticate or route the child next to Roteo: another Anthropic key or backend, the
# user's claude.ai login, or their own Claude Code config directory (which holds that login).
FOREIGN_AUTH = ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_FOUNDRY_API_KEY',
                'ANTHROPIC_CUSTOM_HEADERS', 'CLAUDE_CODE_OAUTH_TOKEN', 'CLAUDE_CODE_USE_BEDROCK',
                'CLAUDE_CODE_USE_VERTEX', 'CLAUDE_CODE_USE_FOUNDRY', 'CLAUDE_CONFIG_DIR')


class RoteoKeyMissing(RuntimeError):
    """The active profile has no ROTEO_API_KEY; raised before any process or request starts."""
    status_code = 401  # an auth failure retrying cannot fix


def hermes_home():
    """The active profile's home. Per call, so a multi-profile gateway resolves each turn's profile."""
    try:
        from hermes_cli.config import get_hermes_home
        return Path(get_hermes_home())
    except Exception:
        home = os.environ.get('HERMES_HOME')
        # Installed as <home>/plugins/<name>/roteo.py.
        return Path(home) if home else Path(__file__).resolve().parents[2]


def _dotenv_value(name):
    path = hermes_home() / '.env'
    try:
        from agent.secret_scope import load_env_file
        return load_env_file(path).get(name)
    except Exception:
        pass
    try:
        lines = path.read_text(encoding='utf-8-sig').splitlines()
    except OSError:
        return None
    for line in lines:
        key, sep, value = line.strip().partition('=')
        if sep and key.strip() == name:
            return value.strip().strip('"').strip("'")
    return None


def secret(name):
    """A profile-scoped value: Hermes' secret scope where this thread has one, else the profile .env.

    Hermes 0.22's host gateway keeps each profile's .env in a per-turn scope rather than os.environ,
    and ``get_secret`` raises on a worker thread that scope does not reach (the native stream runs on one).
    """
    try:
        from agent.secret_scope import get_secret
        value = get_secret(name)
    except Exception:
        value = None
    return (value or _dotenv_value(name) or '').strip() or None


def base_url(setting=None):
    url = (setting.strip() if isinstance(setting, str) else '') or secret(URL_ENV) or DEFAULT_BASE_URL
    url = url.rstrip('/')
    # Plain http only to this machine (a local gateway); the bearer token must not cross a network in clear.
    if not (url.startswith('https://') or url.startswith(('http://127.0.0.1', 'http://localhost'))):
        raise ValueError(f'Roteo base URL must use https: {url}')
    return url


def config_dir():
    """Claude Code's own config directory for this profile, kept apart from the user's own login."""
    path = hermes_home() / PLUGIN_ID / 'claude-config'
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def apply(env, url_setting=None):
    """Point a Claude Code child env at Roteo, in place. Raises RoteoKeyMissing without a key."""
    key = secret(KEY_ENV)
    if not key:
        raise RoteoKeyMissing(KEY_HINT)
    for name in FOREIGN_AUTH:
        env.pop(name, None)
    env.update(ANTHROPIC_BASE_URL=base_url(url_setting), ANTHROPIC_AUTH_TOKEN=key,
               ANTHROPIC_CUSTOM_HEADERS=f'{CLIENT_HEADER}: hermes-roteo/{VERSION}', CLAUDE_CONFIG_DIR=config_dir())
    return env


def upstream_hint(status):
    """A next step for a Roteo answer the user can act on, else ''."""
    return {401: REJECTED_KEY_HINT, 402: BALANCE_HINT}.get(status, '')
