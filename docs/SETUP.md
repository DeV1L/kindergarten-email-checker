# Setup guide

This guide creates the accounts that the tool needs. Then it starts the tool on a VPS or on Kubernetes.

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

## 5. Run the tool on the VPS

The VPS needs only `compose.yaml` and `.env`. It does not build the image. It pulls the public image from ghcr.io. No login is needed.

1. Create a directory for the tool:

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

5. Edit `.env`. Set these values:

| Variable | Value |
|----------|-------|
| `IMAP_USER` | `<dedicated address>` |
| `IMAP_PASSWORD` | `<app password>` |
| `ALLOWED_SENDERS` | The kindergarten addresses or `@domain` suffixes |
| `LLM_API_KEY` | `<DeepSeek key>` |
| `TELEGRAM_BOT_TOKEN` | `<bot token>` |
| `TELEGRAM_CHAT_ID` | `<chat id>` |

6. Pull the image and start the container:

```bash
docker compose pull && docker compose up -d
```

7. Follow the logs:

```bash
docker compose logs -f
```

## 6. Run the tool on Kubernetes (optional)

The Helm chart is in [charts/kindergarten-email-checker](../charts/kindergarten-email-checker). It runs the same image as `compose.yaml`. It uses the same `.env`. Run the commands from the root of a clone of the repository.

CAUTION: run only one instance for each mailbox. When the VPS container and the cluster read the same mailbox, one email can get two posts. Stop the VPS container first, or use a different mailbox and group for the test.

1. Create a namespace:

```bash
kubectl create namespace kindergarten
```

2. Write the values in `.env` without quotes. `--from-env-file` does not remove quotes.
3. Create a secret from `.env`:

```bash
kubectl -n kindergarten create secret generic kindergarten-email-checker --from-env-file=.env
```

4. Install the chart:

```bash
helm upgrade --install kindergarten-email-checker charts/kindergarten-email-checker -n kindergarten
```

5. Follow the logs:

```bash
kubectl -n kindergarten logs -f deployment/kindergarten-email-checker
```

## Settings

All settings come from `.env`. [.env.example](../.env.example) lists every variable with a comment.

| Variable | Meaning |
|----------|---------|
| `IMAP_USER`, `IMAP_PASSWORD` | The address of the dedicated mailbox and its app password |
| `ALLOWED_SENDERS` | Comma-separated addresses or `@domain` suffixes. The tool moves email from all other senders to `Ignored` |
| `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | The Anthropic-compatible endpoint of DeepSeek, the key and the model |
| `LLM_EFFORT` | Thinking effort: `low`, `high` or `max` |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | The bot token and the group id |
| `SWEEP_MINUTES` | Interval of the sweep, for the case that IDLE delivers nothing |
| `MAX_ATTACHMENT_MB` | The tool does not send larger attachments to the model. The post still lists their names |
| `MAX_RETRIES_PER_MESSAGE` | Attempts before the tool moves an email to `Failed` |
| `IMAGE_TAG` | Image tag to run with Compose, default `latest` |
| `TZ` | Timezone for the dates in emails, default `America/Argentina/Buenos_Aires` |
