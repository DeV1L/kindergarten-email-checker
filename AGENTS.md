# Rules for AI agents in this repository

This project reads the emails of a kindergarten in Spanish from a dedicated Gmail account over IMAP. DeepSeek summarizes each email in Russian, with urgency and dates. The tool posts the summary to a private Telegram group. It is one Python process in a Docker container on a VPS.

Start with `README.md`, `docs/SETUP.md` and `docs/OPERATIONS.md`. They describe the setup and the daily tasks. `docs/ARCHITECTURE.md` describes the design, the module map and the failure handling.

## Hard rules

- Do not commit and do not push. The owner commits.
- The tool reads only the dedicated mailbox. Never add code that touches the personal mailbox.
- Gmail labels are the only state. No database, no files that must survive a restart.
- Secrets come only from `.env`. Never log a secret, never put a secret into the image. Never print a secret value in your output.
- Keep the code plain and simple. No abstraction for one caller, no setting for a constant, no framework where a function is enough.

## Model and posts

- The model is DeepSeek `deepseek-flash`, called in the Anthropic Messages API format: the `anthropic` SDK with a custom `base_url`.
- Thinking stays on. Do not turn it off.
- `tool_choice` stays `auto`. DeepSeek rejects a forced tool choice when thinking is on.
- Summaries are in Russian. Proper nouns stay as written.
- The tool sends every post the same way. Urgency is only a label. No silent posts, no pinning.
- The post names the attachments. The tool never uploads them to Telegram.

## Layout

| Path | Content |
|------|---------|
| `src/kindergarten_email_checker/main.py` | Entry point and the loop |
| `src/kindergarten_email_checker/config.py` | Settings from environment variables |
| `src/kindergarten_email_checker/mail.py` | IMAP (imap-tools) |
| `src/kindergarten_email_checker/content.py` | Email to text and images |
| `src/kindergarten_email_checker/summarize.py` | Output schema and the model call |
| `src/kindergarten_email_checker/telegram.py` | Bot API client |
| `src/kindergarten_email_checker/prompt.md` | System prompt |
| `tests/` | Unit tests (pytest) |
| `charts/kindergarten-email-checker/` | Helm chart for Kubernetes, one Deployment |
| `.github/workflows/ci.yml` | Tests on pull requests, image build and push to GHCR on merges to `main` |

## Commands

Run these commands from the repository root:

1. `pip install -e ".[dev]"`
2. `ruff check . && ruff format --check .`
3. `pytest`
4. `docker build -t kindergarten-email-checker .`

On the VPS: `docker compose pull && docker compose up -d`.

## Development rules

- When the logic changes, update the documentation in the same commit: `README.md`, `docs/SETUP.md`, `docs/OPERATIONS.md`, `docs/ARCHITECTURE.md` and `.env.example`, as applicable. The documentation describes how the tool works now.
- Commit messages are brief: one line.

## Git workflow

- Never commit to `main`.
- Every change goes in a branch: `feature/<short-name>` for new behaviour, `fix/<short-name>` for bug fixes.
- Changes reach `main` only through a pull request.

## Documentation rules

Write plain English, about 70 % of the way to ASD-STE100:

- Short sentences. At most 20 words in a procedure step, 25 in a description.
- One instruction per sentence. Start a step with a verb: "Open", "Run", "Copy".
- Active voice and present tense.
- One word for one thing. Use the glossary below. Do not use synonyms for these terms.
- No idioms, no filler words, no "please", no humour.
- Write the full form, not a contraction: "do not", not "don't".
- Explain an abbreviation the first time you use it.
- Use a numbered list for steps and a table for options.
- Put a warning before the step it belongs to, in the form "CAUTION: ...".
- Commands are exact and complete. Put each command in its own code block.

Glossary:

| Term | Meaning |
|------|---------|
| dedicated mailbox | The Gmail account that only this tool uses |
| personal mailbox | The mailbox of the owner. The tool never reads it |
| forwarding filter | The filter in the personal mailbox that forwards the kindergarten emails to the dedicated mailbox |
| allowlist | The sender addresses in `ALLOWED_SENDERS` |
| label | A Gmail label that holds state: `INBOX`, `Processed`, `Ignored` or `Failed` |
| group | The private Telegram group |
| post | A message that the bot sends to the group |
| summary | The model output for one email |
| sweep | The check of the mailbox after each `SWEEP_MINUTES` |
| owner | The person who runs this project |
