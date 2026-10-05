# kindergarten-email-checker

Reads the emails a kindergarten sends in Spanish, writes a short summary in Russian with urgency, deadline and event date, and posts it to a private Telegram group. Runs as one Docker container on a VPS and touches only a dedicated mailbox that receives forwarded kindergarten mail.

The design is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## How it works

1. A filter in a personal mailbox forwards mail from the kindergarten's addresses to a dedicated Gmail account.
2. The container stays connected to the dedicated mailbox and gets each new email when it arrives. It also checks the mailbox every 10 minutes, in case it missed an email.
3. Each unseen email is checked against the sender allowlist, converted to text and sent to DeepSeek (`deepseek-flash`, thinking on) through its Anthropic-compatible API. PDFs and images go along as text or page images.
4. The model returns a structured summary: Russian title and summary, urgency, category, action, deadline, event date.
5. The summary is posted to the Telegram group. If the email has attachments, the post lists their names. Then the email is moved to the `Processed` label.

All posts are sent the same way. Urgency is only a label in the post.

Gmail labels are the only state: `INBOX` is the queue; `Processed`, `Ignored` and `Failed` record the outcome. There is no database.

## Setup

Requirements: a VPS with Docker and Docker Compose, a Google account used only for this tool, a Telegram account and a DeepSeek API key.

### 1. Dedicated Gmail account

1. Create a new Google account, for example `name.kinder@gmail.com`, and use it for nothing else.
2. Turn on 2-Step Verification: Google Account, Security, 2-Step Verification. Google allows app passwords only when 2-Step Verification is on.
3. Create an app password: Google Account, Security, 2-Step Verification, App passwords. Name it `kindergarten-email-checker` and copy the 16-character password. IMAP is enabled by default on Gmail.

### 2. Forwarding filter in the personal mailbox

Gmail:

1. Settings, See all settings, Forwarding and POP/IMAP, Add a forwarding address. Enter the dedicated address. Google sends a confirmation code to the dedicated mailbox; enter it.
2. Settings, Filters and Blocked Addresses, Create a new filter. In From, list the kindergarten addresses separated by OR, for example `direccion@kinder.example OR secretaria@kinder.example`. Choose "Forward it to" and pick the dedicated address. Also tick "Never send it to Spam".

### 3. Telegram bot and group

1. Open a chat with `@BotFather`, send `/newbot`, follow the prompts and copy the token.
2. Create a private group, add the bot to it and post any message in the group.
3. Get the chat id:

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates"
```

Find `"chat":{"id":-100...` in the output. Group ids are negative.

### 4. DeepSeek API key

Create a key at https://platform.deepseek.com and top-up a balance.

### 5. Configure and run on the VPS

```bash
git clone https://github.com/DeV1L/kindergarten-email-checker.git
cd kindergarten-email-checker
cp .env.example .env
chmod 600 .env
```

Edit `.env`: mailbox and app password, the sender allowlist, the DeepSeek key, the Telegram token and chat id. Then:

```bash
docker compose up -d --build
```

Follow the logs:

```bash
docker compose logs -f
```

Update later with:

```bash
git pull && docker compose up -d --build
```

## Configuration

All settings come from `.env`. [.env.example](.env.example) lists every variable with a comment.

| Variable | Meaning |
|---|---|
| `IMAP_USER`, `IMAP_PASSWORD` | Dedicated Gmail address and its app password |
| `ALLOWED_SENDERS` | Comma-separated addresses or `@domain` suffixes. Anything else goes to `Ignored` |
| `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | DeepSeek's Anthropic-compatible endpoint, key and model |
| `LLM_EFFORT` | Thinking effort: `low`, `high` or `max` |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Bot token and the group id |
| `SWEEP_MINUTES` | Fallback poll interval when IDLE delivers nothing |
| `MAX_ATTACHMENT_MB` | Larger attachments are not sent to the model. The post still lists their names |
| `MAX_RETRIES_PER_MESSAGE` | Attempts before an email is moved to `Failed` |
| `TZ` | Timezone used to resolve dates in emails, default `America/Argentina/Buenos_Aires` |

## CI pipeline

The workflow is in [.github/workflows/ci.yml](.github/workflows/ci.yml). It has two jobs.

| Job | What it does | When it runs |
|---|---|---|
| `test` | Ruff lint, Ruff format check, pytest | Manual run from any branch. Pull request opened or updated |
| `image` | Builds the Docker image and pushes it to `ghcr.io/dev1l/kindergarten-email-checker` | Manual run from any branch, after `test` passes. Merge to `main` |

Image tags:

- `latest`: the last build from `main`.
- Branch name, for example `feature-imap-loop`: the last build from that branch.
- `sha-<commit>`: one tag for each build.

To start a manual run: Actions, CI, Run workflow, then select the branch.

## Local development

Python 3.10 or newer. The container uses 3.13.

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
ruff check .
pytest
```

Run the tool locally with a filled `.env` in the project directory:

```bash
python -m kindergarten_email_checker
```
