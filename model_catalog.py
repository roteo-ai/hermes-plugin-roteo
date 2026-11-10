"""Pinned native routes; a loopback gateway needs explicit long-context selection."""
import json
import os
import re
import urllib.request

try:
    from . import roteo
except ImportError:
    import roteo

CONTEXT_WINDOWS = {
    'claude-sonnet-5-5': 1_000_000,
    'claude-sonnet-5': 1_000_000,
    'claude-haiku-5-5': 1_000_000,
    'claude-haiku-4-5-20251001': 200_000,
    'claude-opus-5-5': 1_000_000,
    'claude-opus-5': 1_000_000,
    'claude-opus-4-8': 1_000_000,
    'claude-fable-5-2': 1_000_000,
    'claude-fable-5-1': 1_000_000,
    'claude-mythos-5-1': 1_000_000,
}
# Models Anthropic grants per organization (Mythos: verified organizations only,
# https://platform.claude.com/docs/en/models/mythos-5-1/overview). They are pinned for their window,
# thinking policy and capabilities like any route, but the picker lists one only when the account's
# own picker offers it: never appended from this table, never in the static fallback list.
ACCESS_GATED = frozenset({'claude-mythos-5-1'})
# Families that 400 on ``thinking: {"type": "disabled"}`` (the same contract Hermes core keeps
# in agent/anthropic_adapter.py). A caller's disable is omitted for them, which beats a dead
# request. That does not turn thinking off, so request_body asks for the lowest effort instead
# (`output_config.effort: low`, then `--effort low`): without it a reasoning-off request carries no
# effort and the model thinks at native's default. Opus 5.5 joined Fable: the docs say thinking
# cannot be turned off there and the API answers the disable with the same 400 (#22). Plain Opus 5
# still accepts it, so the entry is the full `claude-opus-5-5` prefix. Sonnet 5.5 rejects the
# disable too (its lowest setting is `between_tools`); plain Sonnet 5 still accepts it. The docs
# say thinking cannot be turned off on Haiku 5.5 either; Haiku 4.5 still accepts the disable.
# Mythos 5.1 documents thinking as "Adaptive (always on)", its picker row says supportsThinkingOff:
# false, and the disable 400s live. Mythos 5 keeps Fable 5's always-on thinking (the 5.1 migration
# guide), so the entry is the family, as in core.
MANDATORY_THINKING = ('claude-fable', 'claude-opus-5-5', 'claude-sonnet-5-5', 'claude-haiku-5-5', 'claude-mythos')
ALIASES = {
    'sonnet': 'claude-sonnet-5-5',
    'haiku': 'claude-haiku-5-5',
    'claude-haiku-4-5': 'claude-haiku-4-5-20251001',
    'opus': 'claude-opus-5-5',
    'fable': 'claude-fable-5-2',
}
# Haiku 4.5 rejects `thinking: {'type': 'adaptive'}` with a 400 upstream; its effort signal
# still applies. Unknown routes keep adaptive so future models are not silently downgraded.
NO_ADAPTIVE_THINKING = frozenset({'claude-haiku-4-5-20251001'})

# ROTEO: the family short names follow Roteo's live model list, so a model Roteo adds reaches every
# Hermes user the day it goes live, with no plugin release and nothing for them to update. Claude
# Code itself is no help here: behind any ANTHROPIC_BASE_URL it maps `fable`, `opus` & co. through
# its own gateway table, which lags the newest models. The tables above stay the offline baseline:
# the read is one unauthenticated GET of `<base>/v1/models` at load, 2 s at most, and any failure
# keeps them as they are. Set ROTEO_LIVE_CATALOG=0 to skip it (the test suite does).
LIVE_CATALOG_ENV = 'ROTEO_LIVE_CATALOG'
LIVE_CATALOG_TIMEOUT = 2.0
_FAMILY_ID = re.compile(r'^claude-(opus|sonnet|haiku|fable)-(\d+)(?:-(\d{1,2}))?$')


def newest_per_family(rows):
    """``{family: (id, window)}``: the newest plain ``claude-<family>-<major>[-<minor>]`` id in a
    ``/v1/models`` list, with its context window. Dated snapshots, `-batch` and other suffixes never
    match, and a row without a window the native routes know (1M or 200K) is skipped rather than
    guessed at."""
    best = {}
    for row in rows if isinstance(rows, list) else ():
        model = str(row.get('id') or '') if isinstance(row, dict) else ''
        match = _FAMILY_ID.match(model)
        window = row.get('max_input_tokens') if match else None
        if not match or window not in (1_000_000, 200_000):
            continue
        family, version = match.group(1), (int(match.group(2)), int(match.group(3) or 0))
        if family not in best or version > best[family][0]:
            best[family] = (version, model, window)
    return {family: (model, window) for family, (_, model, window) in best.items()}


def live_rows(timeout=LIVE_CATALOG_TIMEOUT):
    """Roteo's ``/v1/models`` rows, or None (switched off, offline, or any unexpected answer)."""
    if os.environ.get(LIVE_CATALOG_ENV, '').strip() == '0':
        return None
    try:
        url = roteo.base_url() + '/v1/models'
        request = urllib.request.Request(url, headers={
            'accept': 'application/json', roteo.CLIENT_HEADER: f'hermes-roteo/{roteo.VERSION}'})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            rows = json.loads(response.read(2_000_000)).get('data')
    except Exception:
        return None
    return rows if isinstance(rows, list) else None


def follow_live_catalog(rows):
    """Point each family short name at Roteo's newest model of that family, pinned at the window
    Roteo reports; a route the tables above already pin keeps its pinned window."""
    for family, (model, window) in newest_per_family(rows).items():
        CONTEXT_WINDOWS.setdefault(model, window)
        ALIASES[family] = model


follow_live_catalog(live_rows())


def _route_base(base):
    """The catalogued id a short name points at, or the name unchanged when it points at none.

    `sonnet-5-5` and `sonnet-5.5` both name `claude-sonnet-5-5`; without this they are sent to the
    CLI as typed and the CLI 404s. A name that matches nothing is returned as typed, so an unknown
    route still reaches the CLI and fails there instead of being guessed at.
    """
    if base in ALIASES or base in CONTEXT_WINDOWS:
        return base
    dotted = base.replace('.', '-')
    if dotted != base:
        return _route_base(dotted)
    without_vendor = base.removeprefix('claude-')
    # `haiku-4-5` names the `claude-haiku-4-5` alias, not a pinned id, so check both tables.
    if 'claude-' + without_vendor in CONTEXT_WINDOWS or 'claude-' + without_vendor in ALIASES:
        return 'claude-' + without_vendor
    return base


def native_model(model):
    base = model.removesuffix('[1m]')
    # A short name that names a pinned route must land on it. `sonnet` does, but `sonnet-5-5` and
    # `sonnet-5.5` do not: they miss ALIASES, so the route is sent to the CLI verbatim and the CLI
    # answers 404. A 404 is a hard failure, so Hermes abandons the provider and falls back.
    base = _route_base(base)
    canonical = ALIASES.get(base, base)
    window = CONTEXT_WINDOWS.get(canonical)
    if window == 1_000_000:
        return canonical + '[1m]'
    if window == 200_000:
        if model.endswith('[1m]'):
            raise ValueError('Haiku 4.5 does not support a 1M context window')
        return canonical
    return model


def accepts_thinking_disable(model):
    # Same tolerance as supports_adaptive_thinking: an absent model still reaches `model is required`.
    base = _route_base(model.removesuffix('[1m]')) if isinstance(model, str) else ''
    return not ALIASES.get(base, base).startswith(MANDATORY_THINKING)


def supports_adaptive_thinking(model):
    # Body assembly precedes model validation, so an absent or invalid route answers True
    # and still reaches the existing `model is required` error.
    base = _route_base(model.removesuffix('[1m]')) if isinstance(model, str) else ''
    return ALIASES.get(base, base) not in NO_ADAPTIVE_THINKING


MODEL_METADATA = {
    native_model(model): {'canonical_model': model, 'context_window': window}
    for model, window in CONTEXT_WINDOWS.items()
}
# The routes every account may be offered: the static fallback picker and the rows discovery appends
# when the live picker omits them. Access-gated models come only from the account's own picker.
PICKER_ROUTES = tuple(route for route, meta in MODEL_METADATA.items() if meta['canonical_model'] not in ACCESS_GATED)


def _session_ids(canonical):
    """Every id a session may carry for a pinned route: core looks capabilities up by exact id."""
    aliases = [alias for alias, target in ALIASES.items() if target == canonical]
    ids = {canonical, native_model(canonical), *aliases}
    if CONTEXT_WINDOWS[canonical] == 1_000_000:
        ids.update(alias + '[1m]' for alias in aliases)
    return ids


# Declared with the window: a declared model without one falls to core's 200K unknown-model
# default in the capability lookup (dashboard model info). Unpinned ids keep the catalog path.
MODEL_CAPABILITIES = {
    model_id: {'supports_vision': True, 'context_window': window}
    for canonical, window in CONTEXT_WINDOWS.items()
    for model_id in _session_ids(canonical)
}
