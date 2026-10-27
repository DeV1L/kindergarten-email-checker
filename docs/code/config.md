# config.py

Source: [src/kindergarten_email_checker/config.py](../../src/kindergarten_email_checker/config.py)

## Purpose

`config.py` holds every setting of the app and its default value. It reads the values from environment variables and from the file `.env`. It also holds the allowlist logic, because the allowlist is a setting.

## Who runs it

| Caller | How |
|--------|-----|
| `main.run()` | Creates the one `Settings` object at start. Every other function gets this object as the argument `settings` |
| `main.process()` | Calls `settings.sender_allowed()` for each email |
| Tests | `tests/helpers.py` `make_settings()` creates `Settings(_env_file=None, ...)`, so the tests do not read a real `.env` |

The app reads the settings only once, at start. A changed setting needs a restart.

## Layout

| Item | Kind |
|------|------|
| Module docstring | Points to `.env.example` |
| `Settings`, `model_config` | Class and its pydantic-settings configuration |
| Fields | One field for each setting, in groups |
| `_strip_spaces()` | Field validator |
| `allowed_sender_addresses` | Property |
| `sender_allowed()` | Method |

### Why `Settings` is a class

pydantic-settings reads environment variables into the fields of a `BaseSettings` subclass. The class gives four things that a dict does not give:

- each field maps to the environment variable with the same name in capital letters, for example `imap_user` to `IMAP_USER`;
- the type annotation converts the text value, for example `POLL_MINUTES=10` to the integer 10;
- a field without a default is required. When it is missing, `Settings()` fails at start with a list of the missing fields;
- the defaults are in one place in the code.

### `model_config`

| Option | Value | Effect |
|--------|-------|--------|
| `env_file` | `.env` | Reads `.env` from the current directory, when the file exists. An environment variable wins over the same name in `.env` |
| `env_file_encoding` | `utf-8` | |
| `extra` | `ignore` | Unknown names in `.env` do not cause an error. `.env` also holds `IMAGE_TAG`, which only Docker Compose reads |

In the container there is no `.env` file. Docker Compose (`env_file: .env`) and the Kubernetes secret (`envFrom`) give the values as environment variables.

### How the values are read

The app code does not read environment variables itself. `main.run()` calls `Settings()`, and the library pydantic-settings reads the values. It checks the sources in this order. The first source that has a value wins:

1. Arguments to `Settings(...)`. Only the tests use them.
2. Environment variables of the process. `EnvSettingsSource` reads `os.environ`. Names are case-insensitive: `POLL_MINUTES` fills `poll_minutes`.
3. The file `.env`. `DotEnvSettingsSource` reads the file that `env_file` names.
4. The default in `config.py`.

`BaseSettings.settings_customise_sources()` sets this order. `Settings` does not override it.

| Deployment | Source of the values |
|------------|----------------------|
| Local run | The file `.env` in the current directory |
| Docker Compose | Environment variables. Compose reads `.env` on the host and gives each line to the container |
| Kubernetes | Environment variables. `envFrom` gives each key of the secret to the container |

On Kubernetes, the chart also sets variables with `env`, for example `HEALTH_PORT`. When a name is in `env` and in `envFrom`, Kubernetes uses the value from `env`.

### Fields

The fields are in groups, in this order. Required fields have no default and are secrets or account data.

Dedicated mailbox:

| Field | Default | Meaning |
|-------|---------|---------|
| `imap_host` | `imap.gmail.com` | IMAP server |
| `imap_user` | Required | Address of the dedicated mailbox |
| `imap_password` | Required, secret | App password. Spaces are removed |
| `imap_folder_inbox` | `INBOX` | The label that holds the queue |
| `imap_folder_processed` | `Processed` | Label for posted emails |
| `imap_folder_ignored` | `Ignored` | Label for emails from senders not on the allowlist |
| `imap_folder_failed` | `Failed` | Label for emails that failed `MAX_RETRIES_PER_MESSAGE` times |
| `allowed_senders` | Empty | The allowlist, comma-separated. Empty means that every email goes to `Ignored` |
| `imap_timeout_seconds` | 60 | Socket timeout of one IMAP command |

Model:

| Field | Default | Meaning |
|-------|---------|---------|
| `llm_base_url` | `https://api.deepseek.com/anthropic` | Base URL of the Anthropic Messages API format at DeepSeek |
| `llm_api_key` | Required, secret | DeepSeek API key |
| `llm_model` | `deepseek-flash` | Model name |
| `llm_effort` | `high` | Thinking effort, sent as `output_config.effort` |
| `llm_timeout_seconds` | 120 | Timeout of one model request |
| `llm_tool_name` | `report_summary` | Name of the tool that returns the summary. Also replaces `{TOOL_NAME}` in `prompt.md` |
| `llm_max_tokens` | 16,000 | Output limit for thinking and the tool call together |
| `llm_model_tries` | 2 | Model calls for one email when the answer is unusable. Read "Model try" in [README.md](README.md#model-try) |
| `llm_balance_timeout_seconds` | 30 | Timeout of the balance check at start |

Telegram:

| Field | Default | Meaning |
|-------|---------|---------|
| `telegram_bot_token` | Required, secret | Bot token. It is part of every Bot API URL |
| `telegram_chat_id` | Required | Id of the group, a negative number. The app sends it to the Bot API as it is |
| `telegram_base_url` | `https://api.telegram.org` | Bot API server |
| `telegram_max_message_chars` | 4096 | Telegram's limit for one message |
| `telegram_max_error_chars` | 500 | Length of the error text in an error post |
| `telegram_timeout_seconds` | 30 | Timeout of one Bot API request |

Content extraction:

| Field | Default | Meaning |
|-------|---------|---------|
| `min_image_bytes` | 20,480 (20 KB) | Smaller images are logos and signature graphics. They are skipped |
| `max_pdf_pages_rendered` | 10 | Pages of a scanned PDF rendered as images |
| `pdf_text_min_chars_per_page` | 200 | A PDF with more characters per page on average has a text layer |
| `pdf_render_dpi` | 110 | Resolution of rendered PDF pages |
| `max_body_chars` | 40,000 | Body text is cut at this length |
| `max_pdf_text_chars` | 20,000 | Text of one PDF is cut at this length |

Loop:

| Field | Default | Meaning |
|-------|---------|---------|
| `poll_minutes` | 10 | Pause after each poll |
| `max_attachment_mb` | 10 | Larger attachments are not sent to the model |
| `max_retries_per_message` | 3 | Failed attempts before the label `Failed` |
| `log_level` | `INFO` | Log level. A name that is not a level stops the app at start |
| `tz` | `America/Argentina/Buenos_Aires` | Timezone of the dates in the prompt and the post |

Health checks:

| Field | Default | Meaning |
|-------|---------|---------|
| `health_port` | 8080 | Port of the health server. On Kubernetes the chart sets it |

The app does not check `tz` at start. A wrong timezone name causes an error in `content.extract()` for each email, so each email ends in `Failed`.

### `_strip_spaces(value)`

A field validator on `imap_password`. Gmail shows the app password in four groups of four letters, separated by spaces. The validator removes the spaces, so the owner can copy the password as Gmail shows it.

### `allowed_sender_addresses`

A property. It splits `allowed_senders` at commas, removes spaces, changes the addresses to lower case and drops empty items. A property and not a field, because the source of truth is the text setting.

### `sender_allowed(address) -> bool`

Returns `True` when the address is on the allowlist.


## Constants, limits and flags

All limits of the app are fields of `Settings`. The tables above list them. `.env.example` has the same list, with comments.

## Errors and exit codes

| Situation | Result |
|-----------|--------|
| A required field is missing | `pydantic.ValidationError` in `Settings()`. Exit code 1 with a traceback that names each missing field |
| A value has the wrong type, for example `POLL_MINUTES=ten` | The same |

The module never writes a secret to the log. Its error messages contain the field names, not the values of missing fields.

## Tests

`tests/test_config.py` covers:

- the spaces in the app password are removed;
- the allowlist matches an exact address only, case-insensitive;
- an empty allowlist allows nobody.
