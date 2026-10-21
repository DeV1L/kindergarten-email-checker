# Architecture

This document shows the parts of the app and how they work together.

## Purpose and constraints

The kindergarten sends emails in Spanish almost every day. Most are routine, some are urgent, some carry deadlines. The owner rarely reads email and wants every email turned into a short Russian summary with labels, delivered to a private Telegram group.

Constraints that shaped the design:

- The app must not have access to the owner's personal mailbox.
- Only emails from an allowlist of kindergarten senders are processed.
- Simple and cheap: one container, no database, no extra services.
- Model: DeepSeek `deepseek-flash` with thinking enabled.

## System overview

```mermaid
flowchart LR
    K[Kindergarten] -->|Spanish emails| P["Personal mailbox<br/>forwarding filter"]
    P -->|forwarded copy| G[("Dedicated Gmail<br/>labels: INBOX, Processed, Ignored, Failed")]
    subgraph VPS ["Server"]
        C["Docker container<br/>Python, IMAP IDLE loop"]
    end
    G <-->|IMAP 993| C
    C -->|Anthropic Messages API| D["DeepSeek API<br/>deepseek-flash, thinking on"]
    C -->|Bot API| T["Telegram group"]
```

The container makes outbound connections only: IMAP to Gmail, HTTPS to DeepSeek and Telegram.

## Components

| Component | Responsibility | Where |
|---|---|---|
| Personal mailbox | One filter forwards mail from the kindergarten senders to the dedicated account | Owner's mail provider |
| Dedicated Gmail | Receives forwarded mail. Its labels are the only state (read "State model") | Google, app password over IMAP |
| App container | Long-running Python process: IDLE loop, extraction, model call, Telegram | `src/kindergarten_email_checker/` |
| DeepSeek | Summarization, through the Anthropic Messages API format | `api.deepseek.com/anthropic` |
| Telegram Bot API | Delivery to the private group | `api.telegram.org` |

Module map:

| Module | Role |
|---|---|
| `main.py` | Entry point and the wake, fetch, process, move loop |
| `config.py` | Settings from environment variables, allowlist matching |
| `mail.py` | IMAP session, IDLE wait, fetching unseen mail, moving between labels |
| `content.py` | HTML to text, PDF text extraction, rendering scanned pages, size caps |
| `summarize.py` | Output schema, tool definition, the model call, validation and retry |
| `telegram.py` | Message formatting, sendMessage, error posts |
| `prompt.md` | System prompt |

## Runtime loop

1. On start: connect to IMAP, create the state labels if missing, process everything unseen.
2. Forever: issue IMAP IDLE and wait up to `SWEEP_MINUTES`. Return on new mail or on timeout. Process everything unseen. Repeat.
3. The sweep after a timeout catches anything IDLE missed and refreshes the session, which Gmail drops after roughly 30 minutes anyway.
4. On any IMAP error: close the connection, wait 30 seconds, reconnect. A dropped connection (IMAP abort, socket, SSL or timeout error) is normal: Gmail closes sessions, networks change, laptops sleep. It gets one warning line without a traceback. Any other IMAP error gets a full traceback. The logout after a dropped connection fails too; that error is ignored. The loop never exits on its own.
5. Socket timeouts on IMAP and HTTP calls, so a stalled connection cannot block the loop.

Plain polling is the same loop without the IDLE call. It is the fallback if IDLE misbehaves with Gmail.

## Processing one email

```mermaid
flowchart TD
    A["Wake up<br/>IDLE push or sweep"] --> B["Fetch UNSEEN in INBOX<br/>without setting Seen"]
    B --> C{Sender on the allowlist?}
    C -->|no| I[Move to Ignored]
    C -->|yes| E["Extract content<br/>HTML to text, PDF text, page images, photos"]
    E --> S["DeepSeek call<br/>thinking on, tool call"]
    S --> V{Valid against the schema?}
    V -->|no, first time| S
    V -->|no, second time| F[Send original text to Telegram]
    V -->|yes| T[Post summary to Telegram]
    T --> M[Move to Processed]
    F --> M
```

1. Allowlist: the From address is compared with `ALLOWED_SENDERS`, exact address or `@domain` suffix, case-insensitive. Gmail forwarding keeps the From header intact. A non-matching sender is moved to `Ignored` with no notification.
2. Extraction: read "Content extraction".
3. Model call: read "The model call".
4. Telegram: read "Telegram output".
5. Move to `Processed`. This is the commit point.

## State model

```mermaid
stateDiagram-v2
    [*] --> INBOX: forwarded by the filter
    INBOX --> Ignored: sender not on the allowlist
    INBOX --> Processed: posted to Telegram
    INBOX --> INBOX: transient error, retried next cycle
    INBOX --> Failed: attempts exhausted, error posted
```

- Unseen mail in `INBOX` is the queue. Fetching uses `mark_seen=False`; moving the email is the only state change the app makes.
- Moves use the IMAP MOVE command. After login the app reads the server's capability list again, because Gmail lists MOVE only after login. Without MOVE, the move falls back to copy and delete, and with some Gmail settings the email goes to Trash.
- The app creates the `Processed`, `Ignored` and `Failed` labels at start if they do not exist.
- Telegram is called before the move. A crash between the two produces one duplicate post, never a lost one.
- A per-UID attempt counter lives in memory. After `MAX_RETRIES_PER_MESSAGE` failures the email is moved to `Failed` and the error is posted once. The counter resets on restart, which only grants a few extra attempts.
- No database. Everything the app knows is visible in the Gmail web UI, which doubles as the admin interface.

## Content extraction

| Input | Handling | Reaches the model as |
|---|---|---|
| HTML body | Prefer the text/plain part when present, otherwise html2text | text |
| PDF with a text layer | pypdfium2 text extraction. A text layer counts as present when the average page has more than 200 characters | text |
| PDF without a text layer | pypdfium2 renders each page at about 110 dpi, Pillow saves it as PNG, at most 10 pages | images |
| PDF that cannot be read | Not sent to the model. The file name is listed in the prompt | nothing |
| JPEG, PNG, GIF, WebP | As is. Images under 20 KB are skipped as logos and signature graphics | images |
| Other files | Not sent to the model. The file names are listed in the prompt | nothing |

Caps: attachments above `MAX_ATTACHMENT_MB` are not sent to the model; the request body stays under DeepSeek's 48 MiB limit; body text is truncated at about 40,000 characters with a note.

## The model call

- Endpoint: the Anthropic Messages API format served by DeepSeek at `https://api.deepseek.com/anthropic`, called with the `anthropic` SDK and a custom `base_url`.
- Model: `deepseek-flash` (DeepSeek-V4.1-Flash). Cheapest, accepts images, recommended by DeepSeek. `deepseek-v4-pro` is text-only.
- Thinking: enabled. The request carries `thinking={"type": "enabled", "budget_tokens": 8000}`; DeepSeek ignores `budget_tokens` and reads the effort from `output_config={"effort": LLM_EFFORT}`. The app reads only the tool call from the response. On a retry, the full previous response, thinking blocks included, goes back to the model.
- Output shaping: one tool, `report_summary`, whose `input_schema` is `Summary.model_json_schema()`. The request uses `tool_choice={"type": "auto"}`, and the system prompt tells the model to call the tool exactly once. DeepSeek rejects a forced tool choice when thinking is on (tested 2026-10-05: "Thinking mode does not support this tool_choice"). DeepSeek's Anthropic format has no structured-output mode and no JSON mode, so the tool call carries the schema.
- Validation: `Summary.model_validate(tool_use.input)`. For `action_ru`, `deadline`, `event_date` and `event_time`, the text values "null", "none" and an empty string count as no value. The model sometimes writes the text "null" instead of JSON null. When the model writes tool arguments that are not valid JSON, DeepSeek does not report an error: it returns the tool call with empty input `{}`, which fails validation. On a validation error: one retry with a `tool_result` block that carries the error. On a missing tool call: one retry with the message "Call the report_summary tool." After two failures: subject, sender and original text go to Telegram without a summary, and the email is still moved to `Processed`.
- API errors: the SDK retries timeouts, 429 and 5xx twice. After that the error goes to the main loop, which counts an attempt (read "Failure handling").
- Inputs: the system prompt from `prompt.md`; a user message with a metadata block (From, Subject, sent date in the `TZ` timezone, today's date), the body text, the PDF texts, the list of files not sent to the model, and the image blocks.
- `max_tokens`: 16,000, for thinking and the tool call together. The test call used about 830 output tokens.

Output schema:

| Field | Type | Meaning |
|---|---|---|
| `title_ru` | string | One line, up to 60 characters |
| `summary_ru` | string | At most three short sentences, under 350 characters. No addresses or phone numbers unless needed for the action |
| `urgency` | `low`, `medium`, `high` | How soon the parent must act. `high`: within two days from today, or attendance or schedule changes within two days. `medium`: later. `low`: nothing required, including conditional instructions. The topic does not set urgency |
| `category` | `info`, `event`, `action_required`, `payment`, `closure`, `health`, `other` | Shown in the post; nothing depends on it yet |
| `action_ru` | string or null | What the parent must do |
| `deadline` | date or null | When the parent must have acted |
| `event_date`, `event_time` | date or null, `HH:MM` or null | When the event happens |

Relative dates in the email are resolved by the model from the sent date, which is why the date and the timezone are part of the prompt.

## Telegram output

Post layout, HTML parse mode:

```text
🟡 Medium · 🎉 Мероприятие · ⏰ Срок: пт, 9 окт · 📅 Событие: вт, 20 окт 09:30
<b>Экскурсия в Ботанический сад</b>

summary_ru

<b>Что сделать:</b> action_ru
📎 Вложения: menu.pdf, autorizacion.pdf

<i>Тема: subject · От: sender · Отправлено: пт, 2 окт 2026 14:52</i>
```

Rules:

- Header line: urgency, category, deadline, event date and time. Absent fields are left out.
- Urgency labels: `🔴 High`, `🟡 Medium`, `🟢 Low`.
- Category labels: `ℹ️ Информация`, `🎉 Мероприятие`, `✍️ Нужно действие`, `💰 Оплата`, `🔄 Изменение расписания`, `🩺 Здоровье`, `📌 Другое`.
- All posts are sent the same way, with a normal notification. Urgency is only a label in the header line. Nothing is pinned.
- The post does not quote the original email. The original stays in the dedicated mailbox.
- Attachments: one line with the file names, except skipped small images. The files themselves are not sent.
- Footer: subject, sender and the date the email was sent, with the year and time, in the `TZ` timezone. For a manual forward, this is the date of the forward.
- Fallback post when the model output is unusable: `⚠️ Без сводки`, the attachment names and the original text in an expandable quote. This is the only post that quotes the email, because it has no summary. Telegram's limit is 4096 characters, so the original is trimmed to fit and ends with `…`.
- Log hygiene: Telegram URLs contain the bot token. The app sets the `httpx` and `httpx2` loggers to WARNING and builds Telegram error messages without the URL. The Anthropic SDK uses `httpx2`.
- Error post: `⚠️ Не удалось обработать письмо «subject»: error`, at most once per email.

## Failure handling

IMAP errors are described in "Runtime loop".

| Failure | Behaviour |
|---|---|
| Model timeout, 5xx, 429 | Attempt counter +1, email stays unseen, retried next cycle |
| Model output invalid twice in one attempt | Original text forwarded, email `Processed` |
| Telegram error | Attempt counter +1, email stays unseen |
| Attempts exhausted | Moved to `Failed`, error posted once |
| Process crash | Docker or Kubernetes restarts it. Nothing is lost because the state lives in Gmail |

## Deployment

The app runs as one container from the image `ghcr.io/dev1l/kindergarten-email-checker`. CI builds the image and pushes it to ghcr.io. The host pulls the image and does not build it. There are three deployment options: local development, Docker Compose on a VPS, and Kubernetes with the Helm chart. Exactly one instance runs for each mailbox. The details are in "Start the app" in [SETUP.md](SETUP.md).
