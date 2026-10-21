# kindergarten-email-checker

The app reads the emails that a kindergarten sends in Spanish. Writes a short summary in Russian with urgency, deadline and event date. Posts the summary to a private Telegram group. The tool runs as one Docker container (on a VPS or k8s). It reads only a dedicated mailbox that gets the forwarded kindergarten emails.

## How it works

1. A forwarding filter in the personal mailbox forwards the emails from the kindergarten addresses to the dedicated mailbox.
2. The container stays connected to the dedicated mailbox and gets each new email when it arrives. It also checks the mailbox every 10 minutes (configurable), in case it missed an email.
3. The tool checks each unseen email against the sender allowlist and converts it to text. It sends the text to DeepSeek (`deepseek-flash`, thinking on) through the Anthropic-compatible API. PDFs and images go along as text or page images.
4. The model returns a structured summary: Russian title and summary, urgency, category, action, deadline, event date.
5. The tool posts the summary to the group in Telegram. When the email has attachments, the post lists their names. Then the tool moves the email to the `Processed` label.

The tool sends all posts the same way. Urgency is only a label in the post.

Gmail labels are the only state: `INBOX` is the queue; `Processed`, `Ignored` and `Failed` record the outcome. There is no database.

## Repository structure

| Path | Content |
|------|---------|
| `src/kindergarten_email_checker/` | The Python package and the system prompt |
| `tests/` | Unit tests (pytest) |
| `charts/kindergarten-email-checker/` | The Helm chart for Kubernetes |
| `compose.yaml` | The Docker Compose file for the VPS |
| `Dockerfile` | The container image |
| `.env.example` | The template for `.env`, with every setting |
| `docs/` | Documentation |
| `.github/workflows/` | The CI workflow |
| `AGENTS.md` | Rules for AI agents |

## Requirements

- A Gmail account that only this tool uses
- A Telegram account
- A DeepSeek API key

## Quick start

The full procedure, with every command, is in [docs/SETUP.md](docs/SETUP.md). The steps in short:

1. Create the dedicated mailbox and an app password.
2. Create the forwarding filter in the personal mailbox.
3. Create the Telegram bot and the group.
4. Create the DeepSeek API key.
5. Fill in `.env`.
6. Start the container with `docker compose up -d`.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Setup guide](docs/SETUP.md)
- [Operations guide](docs/OPERATIONS.md)
