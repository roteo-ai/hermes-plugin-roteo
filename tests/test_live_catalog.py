"""ROTEO: the family short names follow Roteo's live model list (model_catalog.follow_live_catalog).

Offline throughout: the live read is driven with a fake ``urlopen``, never the network.
"""
import io
import json

import pytest

import model_catalog
import roteo

LIVE = [
    {'id': 'claude-fable-5', 'max_input_tokens': 1_000_000},
    {'id': 'claude-fable-5-2', 'max_input_tokens': 1_000_000},
    {'id': 'claude-fable-5-1', 'max_input_tokens': 1_000_000},
    {'id': 'claude-opus-5-5', 'max_input_tokens': 1_000_000},
    {'id': 'claude-opus-4-8', 'max_input_tokens': 1_000_000},
    {'id': 'claude-sonnet-5-5', 'max_input_tokens': 1_000_000},
    {'id': 'claude-haiku-5-5', 'max_input_tokens': 1_000_000},
    {'id': 'claude-haiku-4-5', 'max_input_tokens': 200_000},
    {'id': 'gpt-6.1-sol', 'max_input_tokens': 1_000_000},
]


@pytest.fixture
def tables(monkeypatch):
    """Private copies of the two tables, so a test can move a route without leaking it."""
    monkeypatch.setattr(model_catalog, 'ALIASES', dict(model_catalog.ALIASES))
    monkeypatch.setattr(model_catalog, 'CONTEXT_WINDOWS', dict(model_catalog.CONTEXT_WINDOWS))
    return model_catalog


def test_newest_per_family_picks_the_highest_version():
    assert model_catalog.newest_per_family(LIVE) == {
        'fable': ('claude-fable-5-2', 1_000_000),
        'opus': ('claude-opus-5-5', 1_000_000),
        'sonnet': ('claude-sonnet-5-5', 1_000_000),
        'haiku': ('claude-haiku-5-5', 1_000_000),
    }


def test_snapshots_suffixes_and_unknown_windows_never_become_a_family_route():
    rows = [
        {'id': 'claude-opus-9-0-20991231', 'max_input_tokens': 1_000_000},  # dated snapshot
        {'id': 'claude-opus-9-batch', 'max_input_tokens': 1_000_000},       # a price tier, not a model
        {'id': 'claude-opus-9', 'max_input_tokens': 400_000},               # a window the routes do not know
        {'id': 'claude-opus-8', 'max_input_tokens': None},
        {'id': 'claude-mythos-9', 'max_input_tokens': 1_000_000},           # not a short-name family
        'not a row', {'max_input_tokens': 1_000_000},
        {'id': 'claude-opus-5-5', 'max_input_tokens': 1_000_000},
    ]
    assert model_catalog.newest_per_family(rows) == {'opus': ('claude-opus-5-5', 1_000_000)}
    assert model_catalog.newest_per_family(None) == {}


def test_a_model_roteo_adds_moves_the_short_name_and_is_pinned_at_its_window(tables):
    tables.follow_live_catalog(LIVE + [{'id': 'claude-opus-6', 'max_input_tokens': 1_000_000}])
    assert tables.ALIASES['opus'] == 'claude-opus-6'
    assert tables.CONTEXT_WINDOWS['claude-opus-6'] == 1_000_000
    assert tables.native_model('opus') == 'claude-opus-6[1m]'
    assert tables.ALIASES['fable'] == 'claude-fable-5-2'
    # Untouched: the Haiku 4.5 alias, and every route the live list does not name.
    assert tables.ALIASES['claude-haiku-4-5'] == 'claude-haiku-4-5-20251001'
    assert tables.native_model('claude-opus-4-8') == 'claude-opus-4-8[1m]'


def test_a_pinned_window_wins_over_the_live_one(tables):
    tables.follow_live_catalog([{'id': 'claude-sonnet-5-5', 'max_input_tokens': 200_000}])
    assert tables.CONTEXT_WINDOWS['claude-sonnet-5-5'] == 1_000_000
    assert tables.native_model('sonnet') == 'claude-sonnet-5-5[1m]'


def test_no_live_list_keeps_the_pinned_tables(tables):
    before = (dict(tables.ALIASES), dict(tables.CONTEXT_WINDOWS))
    tables.follow_live_catalog(None)
    tables.follow_live_catalog([])
    assert (tables.ALIASES, tables.CONTEXT_WINDOWS) == before
    assert tables.native_model('fable') == 'claude-fable-5-2[1m]'


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def test_live_rows_reads_v1_models_once_with_the_client_header(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen['url'], seen['timeout'] = request.full_url, timeout
        seen['client'] = request.get_header(roteo.CLIENT_HEADER.capitalize())
        seen['auth'] = request.get_header('Authorization')
        return _Response(json.dumps({'object': 'list', 'data': LIVE}).encode())

    monkeypatch.setenv(model_catalog.LIVE_CATALOG_ENV, '1')
    monkeypatch.delenv(roteo.URL_ENV, raising=False)
    monkeypatch.setattr(roteo, 'secret', lambda name: None)
    monkeypatch.setattr(model_catalog.urllib.request, 'urlopen', fake_urlopen)
    assert model_catalog.live_rows() == LIVE
    assert seen['url'] == roteo.DEFAULT_BASE_URL + '/v1/models'
    assert seen['timeout'] == model_catalog.LIVE_CATALOG_TIMEOUT
    assert seen['client'] == f'hermes-roteo/{roteo.VERSION}'
    assert seen['auth'] is None  # the list is public: no key leaves the machine for it


@pytest.mark.parametrize('answer', [
    OSError('offline'),
    b'<html>not json</html>',
    json.dumps({'data': 'nope'}).encode(),
])
def test_live_rows_answers_none_on_any_failure(monkeypatch, answer):
    def fake_urlopen(request, timeout):
        if isinstance(answer, Exception):
            raise answer
        return _Response(answer)

    monkeypatch.setenv(model_catalog.LIVE_CATALOG_ENV, '1')
    monkeypatch.setattr(roteo, 'secret', lambda name: None)
    monkeypatch.setattr(model_catalog.urllib.request, 'urlopen', fake_urlopen)
    assert model_catalog.live_rows() is None


def test_live_rows_is_off_when_switched_off(monkeypatch):
    def fake_urlopen(request, timeout):
        raise AssertionError('must not be called')

    monkeypatch.setenv(model_catalog.LIVE_CATALOG_ENV, '0')
    monkeypatch.setattr(model_catalog.urllib.request, 'urlopen', fake_urlopen)
    assert model_catalog.live_rows() is None
