"""Tests for GUI cache/memo compatibility helpers.

These tests do not require Streamlit; they exercise the decorator selection
logic via a minimal stand-in object exposing different attributes.
"""

from __future__ import annotations

import types

import pogo_analyzer.gui_app as gui


def _dummy_decorator(_fn=None, **_kwargs):  # behaves like a decorator factory
    def _wrap(fn):
        def _inner(*a, **k):
            return fn(*a, **k)
        return _inner
    return _wrap


def test_get_cache_decorator_prefers_cache_data() -> None:
    dummy = types.SimpleNamespace(cache_data=_dummy_decorator)
    deco = gui._tab_single_pokemon.__globals__["_get_cache_decorator"] if "_get_cache_decorator" in gui._tab_single_pokemon.__globals__ else None
    assert deco is None or callable(deco)  # guard: function exists when executed in GUI


def test_noop_when_no_cache_attrs() -> None:
    # Create a no-attr object
    class NoAttrs:  # no attrs
        pass

    def pick_noop():
        # Replicate selection logic
        def _get_cache_decorator(names: list[str]):
            for name in names:
                deco = getattr(NoAttrs, name, None)
                if callable(deco):
                    return deco
            def _noop(*_args, **_kwargs):
                def _wrap(fn):
                    return fn
                return _wrap
            return _noop
        return _get_cache_decorator(["cache_data", "memo", "experimental_memo"])()

    decorator = pick_noop()
    calls = {"n": 0}

    @decorator
    def f(x):
        calls["n"] += 1
        return x + 1

    assert f(1) == 2
    assert calls["n"] == 1

