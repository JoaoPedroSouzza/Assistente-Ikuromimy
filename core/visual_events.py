"""Optional, thread-safe visual notifications; command logic never imports Qt."""
from threading import RLock
import logging
_callbacks = set()
_lock = RLock()

def subscribe(callback):
    with _lock:
        _callbacks.add(callback)
    def unsubscribe():
        with _lock:
            _callbacks.discard(callback)
    return unsubscribe

def publish(event, value=None):
    with _lock:
        callbacks = tuple(_callbacks)
    for callback in callbacks:
        try:
            callback(event, value)
        except Exception:
            logging.getLogger("ikuromimy.visual").debug("visual_observer_unavailable")
