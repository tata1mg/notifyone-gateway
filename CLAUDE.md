# CLAUDE.md

## Project overview

notifyone-gateway is the public-facing API gateway for the NotifyOne notification platform. It accepts inbound notification requests (`POST /send-notification`), validates them, and routes them to the appropriate backend — synchronously for critical-priority events (direct HTTP to notifyone-core) or asynchronously for lower-priority events (AWS SQS queues). It also exposes `GET /get-notification` to query notification status. The gateway is owned by the NotifyOne team and is one component in the larger NotifyOne ecosystem alongside notifyone-core.

---

## Architecture

```
app/
  service.py              # Entry point — registers listeners and blueprints with torpedo.Host
  routes/
    __init__.py           # Collects all blueprints into blueprint_group
    base_api_model.py     # BaseApiModel base class for all route API models
    notifications/
      notification.py     # Sanic Blueprint with send-notification and get-notification endpoints
      api_model.py        # OpenAPI models for the notification endpoints
  services/
    event_notification.py # EventNotification — validates and dispatches notification requests
    notifications.py      # Notifications — in-memory event cache, synced from notifyone-core
    publisher.py          # Publisher abstract interface
  service_clients/
    base_api_client.py    # Base HTTP client
    notifyone_core/
      notification_core.py  # NotifyOneCoreClient — calls to notifyone-core service
  utilities/
    decorators/           # Custom function decorators
    drivers/              # Low-level driver wrappers
    http/
      rest.py             # RestApiClientWrapper — sync HTTP publisher
    pubsub/
      sqs/
        sqs_wrapper.py    # SQSWrapper — async SQS publisher
    validators/
      base.py             # validate_email, validate_mobile helpers
    dataclass.py          # Dataclass utilities
    utils.py              # generate_uuid and other general helpers
  caches/                 # Reserved for caching integrations (currently empty)
  constants/
    constants.py          # PrepareNotification and other shared constants
    error_messages.py     # ErrorMessages enum
    event_priority.py     # EventPriority enum (CRITICAL, HIGH, MEDIUM, LOW)
    notification_channels.py
    notification_request_log_status.py
    process_type.py
  models/
    event.py              # Event dataclass/model
  listeners/
    listener.py           # Sanic server-start listener — calls EventNotification.setup()
    sync_app_events.py    # Periodic app-event sync logic
  exceptions/             # Custom exception classes
  repositories/           # Data repository layer (currently placeholder)
  signals.py              # Sanic signal definitions

tests/
  functional/             # End-to-end tests against a live test Sanic app
    test_send_notification_request.py
    test_get_notification_request.py
  unit/                   # Unit tests for individual components
  mock_resources/
    aws/                  # Mocked SQS setup (moto)
    notifyone_core/       # Mocked notifyone-core HTTP endpoints

conftest.py               # pytest fixtures — test Sanic app, TestClient, mock wiring
config_template.json      # Config schema with all required keys and example values
```

**Entry point:** `app/service.py` (run as `python3 -m app.service`)  
**Blueprint registration:** `app/routes/__init__.py`  
**Listener registration:** `app/listeners/listener.py` (wired in via `Host._listeners`)  
**Notification endpoints:** `app/routes/notifications/notification.py`

---

## Language & runtime

- **Python 3.9**
- **Async** throughout — all service methods and route handlers are `async def`
- **Web framework:** [Sanic](https://sanic.dev/) wrapped by [torpedo](https://github.com/tata1mg/torpedo) (internal framework)
- **Package manager:** `pipenv` (`Pipfile` / `Pipfile.lock`)

---

## Code style & conventions

### Formatting
- 4-space indentation, no tabs
- PEP 8 line length (≤ 88 characters where practical)
- Single quotes for strings

### Naming
- `snake_case` for functions, variables, and module names
- `PascalCase` for classes
- `SCREAMING_SNAKE_CASE` for module-level constants and enum values
- File names: `snake_case.py`

### Import order
1. Standard library
2. Third-party packages
3. Local `app.*` imports

### Error response format
Torpedo/Sanic produces error responses in this shape when raising `BadRequestException` or similar:
```json
{
  "error": { "message": "<human-readable message>" },
  "is_success": false,
  "status_code": 400
}
```
Successful responses follow:
```json
{
  "data": { ... },
  "is_success": true,
  "status_code": 200
}
```
Always use `send_response(data=...)` from torpedo for success responses and raise torpedo exceptions (`BadRequestException`, etc.) for errors — never build raw Sanic responses.

### Route / Blueprint pattern
```python
from sanic import Blueprint
from torpedo import Request, send_response
from torpedo.exceptions import BadRequestException

my_blueprint = Blueprint("my_blueprint")

@my_blueprint.route("/my-endpoint", methods=["POST"], name="my_endpoint")
async def my_handler(request: Request):
    payload = request.custom_json()
    if not payload.get("required_field"):
        raise BadRequestException("missing required parameter - required_field")
    result = await MyService.do_something(payload)
    return send_response(data=result)
```

Register the blueprint in `app/routes/__init__.py` by adding it to `Blueprint.group(...)`.

### Service pattern
Services are class-based with `@classmethod` methods. No instance state.
```python
class MyService:
    @classmethod
    async def do_something(cls, payload: dict):
        ...
```

### API model pattern
Extend `BaseApiModel` for each endpoint. Define `_uri`, `_name`, `_method`, `_summary`, `_description`, and inner `RequestBodyOpenApiModel` / `ResponseBodyOpenApiModel` classes.

### Config / environment pattern
Config is loaded from a JSON file at startup via `torpedo.CONFIG`. Access it as:
```python
from torpedo import CONFIG
my_config = CONFIG.config["MY_SECTION"]
```
Add new config keys to `config_template.json` with placeholder values. Never hardcode secrets.

---

## Git conventions

### Branch naming
```
feat/<short-description>      # new feature
fix/<short-description>       # bug fix
refactor/<short-description>  # no behaviour change
chore/<short-description>     # tooling, deps, config
security/<short-description>  # security hardening
```

### Commit message format
```
<type>(<scope>): short imperative description

- bullet for each logical change
- keep each bullet under 72 chars
```
Examples from this repo:
- `security: run service with limited access user in Dockerfile`
- `fix: add correct year and org name in license`

---

## How to run the project

```bash
# Install dependencies
pipenv sync

# Copy and fill in config
cp config_template.json config.json
# Edit config.json with real values

# Start the service
pipenv run python3 -m app.service
```

The service listens on `0.0.0.0:9401` by default (configured via `config.json`).

---

## How to run tests

```bash
# Full test suite
pipenv run pytest

# Single file
pipenv run pytest tests/functional/test_send_notification_request.py

# With coverage
pipenv run pytest --cov=app --cov-report=term-missing
```

**Test framework:** `pytest` + `pytest-sanic`  
**Test file location:** `tests/functional/` and `tests/unit/`, named `test_*.py`  
**Fixtures:** Defined in `conftest.py` — `test_cli` is the primary fixture for functional tests; it starts a full Sanic test server with mocked external dependencies.  
**Mocking approach:**
- External HTTP calls (notifyone-core) are mocked via a secondary Sanic app in `tests/mock_resources/notifyone_core/`
- AWS SQS is mocked with `moto` — see `tests/mock_resources/aws/mock_sqs.py`
- Always mock external services; do not make real network calls in tests

---

## How to run the linter / formatter

This repo does not currently have a linter configured. Follow PEP 8 manually or configure `flake8`/`ruff` if adding one.

---

## External dependencies

| Service          | Purpose                                      | Local setup                              |
|------------------|----------------------------------------------|------------------------------------------|
| notifyone-core   | Downstream service — event config & delivery | Set `NOTIFICATION_SERVICE.HOST` in config; mock in tests via `MockNotifyOneCoreApis` |
| AWS SQS          | Async notification queue (HIGH/MEDIUM/LOW)   | Use LocalStack: `docker run -p 4566:4566 localstack/localstack`; or use moto in tests |
| Redis            | Rate limiting / caching (planned)            | `docker run -p 6379:6379 redis:alpine`   |

---

## Key files reference

| File                                              | Purpose                                                  |
|---------------------------------------------------|----------------------------------------------------------|
| `app/service.py`                                  | Entry point — wires listeners and blueprints into Host   |
| `app/routes/__init__.py`                          | Blueprint group registration                             |
| `app/routes/notifications/notification.py`        | `POST /send-notification` and `GET /get-notification`    |
| `app/routes/notifications/api_model.py`           | OpenAPI request/response models for notification routes  |
| `app/routes/base_api_model.py`                    | Base class for all API models                            |
| `app/services/event_notification.py`              | Core dispatch logic — validates and routes notifications  |
| `app/services/notifications.py`                   | In-memory event cache with periodic refresh              |
| `app/service_clients/notifyone_core/notification_core.py` | HTTP client for notifyone-core             |
| `app/utilities/pubsub/sqs/sqs_wrapper.py`         | SQS publish wrapper used for async priority queues       |
| `app/utilities/http/rest.py`                      | HTTP publish wrapper used for critical-priority sync path |
| `app/constants/error_messages.py`                 | All user-facing error message strings                    |
| `app/constants/event_priority.py`                 | EventPriority enum (CRITICAL/HIGH/MEDIUM/LOW)            |
| `app/listeners/listener.py`                       | Server-start listener — calls `EventNotification.setup()`|
| `config_template.json`                            | Config schema with all required keys                     |
| `conftest.py`                                     | pytest fixtures for functional tests                     |

---

## Do not touch

- `.github/workflows/` — CI pipeline, managed separately
- `Pipfile.lock` — do not edit manually; regenerate with `pipenv lock`
- Any file with `# DO NOT EDIT` at the top
