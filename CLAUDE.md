# kindergarten-email-checker

Spanish kindergarten emails, read from a dedicated Gmail account over IMAP, summarized in Russian by DeepSeek with urgency and dates, posted to a private Telegram group. One Python process in a Docker container on a VPS.

## Read first

- `README.md`: setup and operations.
- `docs/ARCHITECTURE.md`: design, module map, failure handling, decision log, open questions. Keep it in sync when behaviour changes.

## Layout

- `src/kindergarten_email_checker/main.py`: entry point and loop
- `config.py`: settings from environment variables
- `mail.py`: IMAP (imap-tools)
- `content.py`: email to text and images
- `summarize.py`: output schema and the model call
- `telegram.py`: Bot API client
- `prompt.md`: system prompt
- `tests/`: pytest

## Commands

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
docker compose up -d --build
```

## Development rules

- If any logic changes, update the documentation in the same commit: `README.md`, `docs/ARCHITECTURE.md`, `.env.example` as applicable. The docs describe how the tool works now.
- Keep the project status in `docs/ARCHITECTURE.md`, not in the README.
- Commit messages are brief: one line.
- Documentation is plain, simple English, close to ASD-STE100: short sentences, active voice, one idea per sentence, common words.
- Code is plain and simple. Do not over-engineer: no abstraction for one caller, no setting for a constant, no framework where a function will do.

## Constraints

- Only the dedicated mailbox is ever accessed. Never add code that touches the owner's personal mailbox.
- Gmail labels are the only state. No database, no files that must survive a restart.
- Model: DeepSeek via the Anthropic Messages API format (`anthropic` SDK, custom `base_url`), model `deepseek-flash`, thinking enabled. Do not disable thinking.
- Summaries are Russian; proper nouns stay as written.
- Every Telegram post is sent the same way. Urgency is only a label. No silent posts, no pinning.
- Attachments are named in the post, never uploaded to Telegram.
- Secrets come only from `.env`. Never log them, never bake them into the image.
- Do not commit or push. The owner commits.
