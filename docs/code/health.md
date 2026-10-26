# health.py

Source: [src/kindergarten_email_checker/health.py](../../src/kindergarten_email_checker/health.py)

## Purpose

`health.py` is a small HTTP server for the Kubernetes probes. It answers two paths: `/readyz` and `/livez`. It uses `http.server` from the standard library and runs in a daemon thread. The main loop does not depend on it.

## Who runs it

| Caller | How |
|--------|-----|
| `main.run()` | Calls `start(HEALTH_PORT)` before the start check |
| `main.check_services()` | Sets `health.ready = True` after the start check passes |
| Kubernetes | The readiness probe calls `/readyz` every 10 seconds. The liveness probe calls `/livez` every 60 seconds. The chart sets the port |

On Docker Compose, the server runs too, but nothing calls it.

## Layout

| Item | Kind |
|------|------|
| Module docstring | The two paths |
| `ready` | Module variable |
| `status()` | Function |
| `Handler` | Class |
| `start()` | Function |

### `ready`

A module-level `bool`, `False` at import. `main.check_services()` sets it to `True` once. The server thread reads it. Only one thread writes it, so it needs no lock.

### `status(path) -> int`

Returns the HTTP status for a path:

| Path | Status |
|------|--------|
| `/readyz` | 200 when `ready` is `True`, otherwise 503 |
| `/livez` | Always 200 |
| Any other path | 404 |

The logic is in a function and not in `Handler`, so it is easy to read and to test.

### `Handler`

A subclass of `BaseHTTPRequestHandler`. Why it is a class: `http.server` requires a handler class. It creates one handler object for each request and calls its `do_GET()` method.

| Method | What it does |
|--------|--------------|
| `do_GET()` | Sends the status from `status()` with no body |
| `log_message()` | Does nothing. The probes call every few seconds, and one log line for each call would fill the log |

Other HTTP methods get the default answer of `http.server`: 501.

### `start(port) -> HTTPServer`

Creates an `HTTPServer` on all interfaces and the given port. Starts `serve_forever()` in a daemon thread and returns the server. A daemon thread does not keep the process alive, so the process ends when the main thread ends. Port 0 picks a free port. The tests use it.

## Constants, limits and flags

| Name | Value | Meaning |
|------|-------|---------|
| `HEALTH_PORT` | Setting, 8080 | Port of the server. On Kubernetes, the chart value `healthPort` sets it, and the value in the secret has no effect |
| `ready` | `False`, then `True` | Readiness flag |

## Errors and exit codes

| Situation | Result |
|-----------|--------|
| The port is in use | `OSError` in `start()`. The app stops with exit code 1 before the start check |
| `/readyz` answers 503 | The pod is not ready. The start check did not pass yet |
| No answer on `/livez` | Kubernetes restarts the container |

Only the readiness probe depends on Telegram, Gmail and DeepSeek, and only once, at start. An outage of these services after the start does not change the answers.

## Tests

`tests/test_health.py` starts the server on port 0 and checks: `/readyz` gives 503 before the start check and 200 after, `/livez` gives 200, another path gives 404.
