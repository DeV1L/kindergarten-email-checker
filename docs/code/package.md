# __init__.py and __main__.py

Sources: [src/kindergarten_email_checker/\_\_init\_\_.py](../../src/kindergarten_email_checker/__init__.py), [src/kindergarten_email_checker/\_\_main\_\_.py](../../src/kindergarten_email_checker/__main__.py)

## Purpose

These two files make `kindergarten_email_checker` a package that Python can run.

| File | Content |
|------|---------|
| `__init__.py` | The package docstring and `__version__` |
| `__main__.py` | The entry point for `python -m kindergarten_email_checker` |

## Who runs it

| Caller | How |
|--------|-----|
| The container | `CMD ["python", "-m", "kindergarten_email_checker"]` runs `__main__.py` |
| A local run | `python -m kindergarten_email_checker` |
| `main.run()` | Reads `__version__` for the start line in the log |

`pyproject.toml` also defines the console script `kindergarten-email-checker`. It calls `main.run()` directly, without `__main__.py`.

## Layout

### `__init__.py`

| Item | Kind | Meaning |
|------|------|---------|
| Docstring | Text | One line: what the app does |
| `__version__` | Constant, `"0.1.0"` | Version in the start line of the log |

`__version__` and `version` in `pyproject.toml` are two separate values. Change both together.

### `__main__.py`

Imports `run()` from `main.py` and calls `raise SystemExit(run())`. The return value of `run()` becomes the exit code. The `if __name__ == "__main__"` check stops the call when a test imports the file.

The package has no class.

## Constants, limits and flags

| Name | Value |
|------|-------|
| `__version__` | `0.1.0` |

## Errors and exit codes

`__main__.py` passes the return value of `run()` to `SystemExit`. `run()` returns 0 only in theory, because the loop does not end. Every exit code of the app is in [README.md](README.md#exit-codes).

## Tests

No test covers these files directly.
