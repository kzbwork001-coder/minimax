"""Tests for the EventEmitter."""

from minimax.emitter import EventEmitter
from minimax.schema.events import Event


class TestEventEmitter:
    def test_on_and_emit(self):
        emitter = EventEmitter()
        results = []
        emitter.on(Event.SUCCESSFUL_SYNC, lambda: results.append("synced"))
        emitter.emit(Event.SUCCESSFUL_SYNC)
        assert results == ["synced"]

    def test_emit_with_args(self):
        emitter = EventEmitter()
        results = []
        emitter.on(Event.SUCCESSFUL_LOGIN, lambda token: results.append(token))
        emitter.emit(Event.SUCCESSFUL_LOGIN, "my_token")
        assert results == ["my_token"]

    def test_multiple_listeners(self):
        emitter = EventEmitter()
        results = []
        emitter.on(Event.SUCCESSFUL_SYNC, lambda: results.append("a"))
        emitter.on(Event.SUCCESSFUL_SYNC, lambda: results.append("b"))
        emitter.emit(Event.SUCCESSFUL_SYNC)
        assert results == ["a", "b"]

    def test_off_specific_listener(self):
        emitter = EventEmitter()
        results = []
        listener = lambda: results.append("x")
        emitter.on(Event.SUCCESSFUL_SYNC, listener)
        emitter.off(Event.SUCCESSFUL_SYNC, listener)
        emitter.emit(Event.SUCCESSFUL_SYNC)
        assert results == []

    def test_off_all_listeners(self):
        emitter = EventEmitter()
        results = []
        emitter.on(Event.SUCCESSFUL_SYNC, lambda: results.append("a"))
        emitter.on(Event.SUCCESSFUL_SYNC, lambda: results.append("b"))
        emitter.off(Event.SUCCESSFUL_SYNC)
        emitter.emit(Event.SUCCESSFUL_SYNC)
        assert results == []

    def test_off_nonexistent_listener_no_error(self):
        emitter = EventEmitter()
        listener = lambda: None
        # Should not raise
        emitter.off(Event.SUCCESSFUL_SYNC, listener)

    def test_emit_no_listeners_no_error(self):
        emitter = EventEmitter()
        # Should not raise
        emitter.emit(Event.SUCCESSFUL_SYNC)
