"""
Minimal conftest for unit tests that do not require the full Sanic/torpedo stack.
Stubs out modules that are only available in a full pipenv environment.
"""
import sys
import types


def _stub_module(name, **attrs):
    """Create and register a stub module."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# --- commonutils stubs ---
if "commonutils" not in sys.modules:
    _stub_module("commonutils")

# --- torpedo stubs ---
if "torpedo" not in sys.modules:
    torpedo_mod = _stub_module("torpedo")

    class _FakeConfig:
        config = {
            "TRIGGER_NOTIFICATIONS": {
                "QUEUE_BACKEND": "sqs",
                "SQS": {},
                "KAFKA": {"BOOTSTRAP_SERVERS": "localhost:9092", "MAX_RETRY_ATTEMPTS": 3},
                "CRITICAL_PRIORITY": {"HOST": "http://localhost:9402"},
                "HIGH_PRIORITY": {"QUEUE_NAME": "stag-ns_high_priority_event_notification"},
                "MEDIUM_PRIORITY": {"QUEUE_NAME": "stag-ns_medium_priority_event_notification"},
                "LOW_PRIORITY": {"QUEUE_NAME": "stag-ns_low_priority_event_notification"},
            }
        }

    torpedo_mod.CONFIG = _FakeConfig()
