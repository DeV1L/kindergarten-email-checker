# Setup guide

This guide creates the accounts that the app needs. Then it starts the app in one of three ways: local development, Docker Compose on a VPS, or Kubernetes.

## Values to collect

The steps below produce values that later steps need. The guide refers to them with these placeholders:

| Placeholder | What it is | From step |
|-------------|------------|-----------|
| `<dedicated address>` | The address of the dedicated mailbox | 1 |
| `<app password>` | The 16-character app password of the dedicated mailbox | 1 |
| `<bot token>` | The token of the Telegram bot | 3 |
| `<chat id>` | The id of the group, a negative number | 3 |
| `<DeepSeek key>` | The DeepSeek API key | 4 |

## 1. Create the dedicated mailbox

1. Create a new Google account, for example `name.kinder@gmail.com`. Use it for nothing else. Store the address as `<dedicated address>`.
2. Open **Google Account**, **Security**, **2-Step Verification**. Turn on 2-Step Verification. Google allows app passwords only when 2-Step Verification is on.
3. Open **Google Account**, **Security**, **2-Step Verification**, **App passwords**.
4. Enter the name `kindergarten-email-checker`. Copy the 16-character password. Store it as `<app password>`.

IMAP is on by default in Gmail.

## 2. Create the forwarding filter

These steps are for a personal mailbox in Gmail.

1. In the personal mailbox, open **Settings**, **See all settings**, **Forwarding and POP/IMAP**.
2. Click **Add a forwarding address**. Enter `<dedicated address>`.
3. Google sends a confirmation code to the dedicated mailbox. Enter the code.
4. Open **Settings**, **Filters and Blocked Addresses**, **Create a new filter**.
5. In **From**, enter the kindergarten addresses. Separate them with `OR`, for example `direccion@kinder.example OR secretaria@kinder.example`.
6. Select **Forward it to**. Select `<dedicated address>`.
7. Select **Never send it to Spam**.

## 3. Create the Telegram bot and the group

1. Open a chat with `@BotFather`. Send `/newbot`. Follow the prompts.
2. Copy the token. Store it as `<bot token>`.
3. Create a private group. Add the bot to the group.
4. Post any message in the group.
5. Get the updates of the bot:

```bash
curl -s "https://api.telegram.org/bot<bot token>/getUpdates"
```

6. Find `"chat":{"id":-100...` in the output. Store the number as `<chat id>`. Group ids are negative.

## 4. Create the DeepSeek API key

1. Open https://platform.deepseek.com.
2. Create an API key. Store it as `<DeepSeek key>`.
3. Add money to the balance.

## 5. Settings

The app reads all settings from environment variables. All three deployment options get them from the file `.env`. The template is [.env.example](../.env.example), with a comment for each variable. Step 6 tells where to create `.env` for each option.

Set these values in `.env`:

| Variable | Value |
|----------|-------|
| `IMAP_USER` | `<dedicated address>` |
| `IMAP_PASSWORD` | `<app password>` |
| `ALLOWED_SENDERS` | The kindergarten addresses, separated by commas. Only an exact address matches. The app moves email from all other senders to `Ignored` |
| `LLM_API_KEY` | `<DeepSeek key>` |
| `TELEGRAM_BOT_TOKEN` | `<bot token>` |
| `TELEGRAM_CHAT_ID` | `<chat id>` |

The other variables have defaults:

| Variable | Default | Meaning |
|----------|---------|---------|
| `IMAP_HOST` | `imap.gmail.com` | The IMAP server of the dedicated mailbox |
| `IMAP_FOLDER_INBOX`, `IMAP_FOLDER_PROCESSED`, `IMAP_FOLDER_IGNORED`, `IMAP_FOLDER_FAILED` | `INBOX`, `Processed`, `Ignored`, `Failed` | The names of the labels |
| `IMAP_TIMEOUT_SECONDS` | `60` | Timeout of one IMAP command |
| `LLM_BASE_URL` | `https://api.deepseek.com/anthropic` | The Anthropic-compatible endpoint of DeepSeek |
| `LLM_MODEL` | `deepseek-flash` | The model |
| `LLM_EFFORT` | `high` | Thinking effort: `low`, `high` or `max` |
| `LLM_TIMEOUT_SECONDS` | `120` | Timeout of one model call |
| `LLM_TOOL_NAME` | `report_summary` | The name of the tool that returns the summary. The app puts the same name into the system prompt |
| `LLM_MAX_TOKENS` | `16000` | Output limit of one model call, for thinking and the tool call together |
| `LLM_MODEL_TRIES` | `2` | Model calls for one email. The app calls the model again only when the answer is unusable |
| `LLM_BALANCE_TIMEOUT_SECONDS` | `30` | Timeout of the DeepSeek balance check at start |
| `TELEGRAM_BASE_URL` | `https://api.telegram.org` | The Telegram Bot API server |
| `TELEGRAM_MAX_MESSAGE_CHARS` | `4096` | Telegram's limit for one message. The app trims longer posts |
| `TELEGRAM_MAX_ERROR_CHARS` | `500` | Length of the error text in an error post. The app trims a longer error text. The log holds the full error |
| `TELEGRAM_TIMEOUT_SECONDS` | `30` | Timeout of one Telegram call |
| `MIN_IMAGE_BYTES` | `20480` | Smaller images are logos and signature graphics. The app skips them |
| `MAX_PDF_PAGES_RENDERED` | `10` | Pages of a scanned PDF that go to the model as images |
| `PDF_TEXT_MIN_CHARS_PER_PAGE` | `200` | A PDF with fewer characters per page goes to the model as page images |
| `PDF_RENDER_DPI` | `110` | Resolution of the page images |
| `MAX_BODY_CHARS` | `40000` | The app trims a longer email body |
| `MAX_PDF_TEXT_CHARS` | `20000` | The app trims a longer PDF text |
| `POLL_MINUTES` | `10` | Minutes between two polls. A new email waits up to this time for its post |
| `MAX_ATTACHMENT_MB` | `10` | The app does not send larger attachments to the model. The post still lists their names |
| `MAX_RETRIES_PER_MESSAGE` | `3` | Attempts before the app moves an email to `Failed` |
| `TZ` | `America/Argentina/Buenos_Aires` | Timezone for the dates in emails and posts |
| `LOG_LEVEL` | `INFO` | Log level of the app and all libraries. At `INFO` and `DEBUG`, the log shows the URL of each Telegram request. This URL contains the bot token |
| `HEALTH_PORT` | `8080` | Port of the health checks `/readyz` and `/livez`. On Kubernetes, the chart value `healthPort` sets it |
| `IMAGE_TAG` | `latest` | The image tag. Only Docker Compose reads it |

## 6. Start the app

Choose one deployment option:

| Option | Where the app runs | Image |
|--------|--------------------|-------|
| Local development | The local computer, in a clone of the repository | No image, or an image built locally |
| Docker Compose | A VPS | Pulled from ghcr.io |
| Kubernetes | A cluster, with the Helm chart | Pulled from ghcr.io |

CI builds the image `ghcr.io/dev1l/kindergarten-email-checker` from the `Dockerfile` and pushes it. The image is public, so a pull needs no login. The image is based on `python:3.13-slim`. pip installs the dependencies from `pyproject.toml`. The app runs as the non-root user `app` (id 10001). The image tags are in "CI pipeline" in the [operations guide](OPERATIONS.md).

CAUTION: run only one instance of the app for each mailbox. Two instances read the same emails, and one email gets two posts. Before you start a second instance for a test, stop the first one, or use a different mailbox and group.

### Local development

The app needs Python 3.10 or newer. The image uses Python 3.13.

1. Clone the repository:

```bash
git clone https://github.com/DeV1L/kindergarten-email-checker.git && cd kindergarten-email-checker
```

2. Create a virtual environment and activate it:

```bash
python3 -m venv .venv && . .venv/bin/activate
```

3. Install the package with the development tools:

```bash
pip install -e ".[dev]"
```

4. Copy the settings template and make it readable only for its owner:

```bash
cp .env.example .env && chmod 600 .env
```

5. Edit `.env`. Set the values from step 5.
6. Run the linter and the format check:

```bash
ruff check . && ruff format --check .
```

7. Run the tests:

```bash
pytest
```

8. Start the app. It reads `.env` from the current directory:

```bash
python -m kindergarten_email_checker
```

To test the image, build it and run it with the same `.env`:

1. Build the image:

```bash
docker build -t kindergarten-email-checker .
```

2. Run the container:

```bash
docker run --rm --env-file .env kindergarten-email-checker
```

### Docker Compose on a VPS

The VPS needs only `compose.yaml` and `.env`. It pulls the image and does not build it. [compose.yaml](../compose.yaml) sets:

| Setting | Value |
|---------|-------|
| Image | `ghcr.io/dev1l/kindergarten-email-checker`, with the tag from `IMAGE_TAG` |
| Restart | `unless-stopped`: Docker starts the container again after a crash or a reboot |
| Root filesystem | Read-only, with a tmpfs at `/tmp` |
| Memory limit | 256 MB |
| Logs | json-file, rotated at 3 files of 10 MB |

1. Create a directory for the app:

```bash
mkdir kindergarten-email-checker && cd kindergarten-email-checker
```

2. Download the Compose file:

```bash
curl -fsSLO https://raw.githubusercontent.com/DeV1L/kindergarten-email-checker/main/compose.yaml
```

3. Download the settings template as `.env`:

```bash
curl -fsSL https://raw.githubusercontent.com/DeV1L/kindergarten-email-checker/main/.env.example -o .env
```

4. Make `.env` readable only for its owner:

```bash
chmod 600 .env
```

5. Edit `.env`. Set the values from step 5.
6. Pull the image and start the container:

```bash
docker compose pull && docker compose up -d
```

7. Check the logs. Read "Follow the logs" in the [operations guide](OPERATIONS.md).

### Kubernetes

The Helm chart is in [charts/kindergarten-email-checker](../charts/kindergarten-email-checker). It creates one Deployment and nothing else: no Service, no ingress, no volume except an `emptyDir` at `/tmp`. The chart sets:

| Setting | Value |
|---------|-------|
| Replicas | Exactly 1, with the `RollingUpdate` strategy: `maxSurge` 1, `maxUnavailable` 0. On an update, the old pod runs until the new pod is ready. Read "Deployment" in [ARCHITECTURE.md](ARCHITECTURE.md) |
| Image | `image.repository` and `image.tag` in the chart values. The default tag is `latest`. `IMAGE_TAG` in `.env` has no effect |
| Pull policy | `Always`. Each `helm upgrade` replaces the pod, so the new pod pulls the image again |
| User | 10001, non-root |
| Security | Read-only root filesystem, no capabilities, no privilege escalation, no service account token |
| Health checks | A readiness probe on `/readyz` and a liveness probe on `/livez`, port 8080. The chart values `readinessPeriodSeconds` (default 10) and `livenessPeriodSeconds` (default 60) set how often they run. Read "Health checks" in the [operations guide](OPERATIONS.md) |
| Resources | Memory request and limit 128 MiB, CPU request 50m |
| Settings | All variables come from an existing secret, `existingSecret` in the chart values, default `kindergarten-email-checker`. The chart does not create or hold secrets. `env` in the chart values overrides single variables |

Run the commands from the root of a clone of the repository.

1. Create a namespace:

```bash
kubectl create namespace kindergarten
```

2. Copy the settings template and make it readable only for its owner:

```bash
cp .env.example .env && chmod 600 .env
```

3. Edit `.env`. Set the values from step 5. Write the values without quotes, because `--from-env-file` does not remove quotes.
4. Create the secret from `.env`:

```bash
kubectl -n kindergarten create secret generic kindergarten-email-checker --from-env-file=.env
```

5. Install the chart:

```bash
helm upgrade --install kindergarten-email-checker charts/kindergarten-email-checker -n kindergarten
```

6. Check the logs. Read "Follow the logs" in the [operations guide](OPERATIONS.md).

#### Deploy from GitHub

The workflow **Deploy** installs or updates the chart from GitHub Actions. It reads a kubeconfig from the GitHub secret `KUBECONFIG`. GitHub runners must reach the API server in the kubeconfig from the internet.

1. In the repository on GitHub, click **Settings**, **Secrets and variables**, **Actions**.
2. Click **New repository secret**. Enter the name `KUBECONFIG`. Paste the content of the kubeconfig. Click **Add secret**.

To deploy, read "Update the app" in the [operations guide](OPERATIONS.md).
