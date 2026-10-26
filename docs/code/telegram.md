# telegram.py

Source: [src/kindergarten_email_checker/telegram.py](../../src/kindergarten_email_checker/telegram.py)

## Purpose

`telegram.py` formats the posts and sends them to the group through the Telegram Bot API. It has three kinds of post: the summary, the fallback with the original text, and the error post. It also holds the Telegram part of the start check.

## Who runs it

| Caller | Function | When |
|--------|----------|------|
| `main.check_services()` | `check()` | Once at start |
| `main.process()` | `send_summary()` | The model returned a `Summary` |
| `main.process()` | `send_original()` | The model returned `None` |
| `main.process()` | `send_error()` | An email failed `MAX_RETRIES_PER_MESSAGE` times |

## Layout

| Item | Kind |
|------|------|
| Module docstring | One line |
| `URGENCY_LABEL`, `CATEGORY_LABEL` | Constants: labels in the header line |
| `WEEKDAYS`, `MONTHS` | Constants: short Russian names for dates |
| `TelegramError` | Exception class |
| `ru_date()` | Function: date format |
| `format_message()` | Function: the summary post |
| `footer()` | Function: the last line of a post |
| `format_original()` | Function: the fallback post |
| `with_original()` | Function: adds the quoted original within the limit |
| `call()` | Function: one Bot API request |
| `check()` | Function: start check |
| `send_message()` | Function: one `sendMessage` request |
| `send_summary()`, `send_original()`, `send_error()` | Functions: format and send |

The formatting functions are pure: they return text and make no requests. The tests check them without a network.

### `TelegramError`

An exception class for a Bot API answer with `"ok": false`. Why it is a class: the error line in the log and in the error post shows the type name, `TelegramError`. The class has no body.

### `ru_date(value) -> str`

Formats a date as weekday and day with the short month in Russian: 2026-10-10 gives `сб, 10 окт`. The month names are in the genitive case, for example `мая`, because they follow the day number. The year is left out.

### `format_message(summary, content, settings) -> str`

Builds the summary post in Telegram HTML:

```text
🟡 Medium · 🎉 Мероприятие · ⏰ Срок: пт, 9 окт · 📅 Событие: вт, 20 окт 09:30
<b>title_ru</b>

summary_ru

<b>Что сделать:</b> action_ru
📎 Вложения: menu.pdf, autorizacion.pdf

<i>Тема: subject · От: sender · Отправлено: пт, 2 окт 2026 14:52</i>
```

1. The header line: urgency label, category label, deadline, event date with the time. A missing deadline or event date is left out.
2. The title in bold and the summary.
3. The action line, only when `action_ru` has a value.
4. The attachment line, only when the email has attachments. It names the files. The files are not sent.
5. The footer from `footer()`.

Every value from the model or the email goes through `html.escape()`, so `<`, `>` and `&` in the text cannot break the HTML. The post does not quote the email.

The function cuts the result at `TELEGRAM_MAX_MESSAGE_CHARS`. The cut does not respect HTML tags. A post that long is rare, because the title and summary have length limits in the prompt.

### `footer(content) -> str`

Returns the last line in italics: subject, sender and send date with the year and time, in the `TZ` timezone.

### `format_original(content, settings) -> str`

Builds the fallback post for an email without a summary. It starts with `⚠️ Без сводки` (no summary) and the attachment line. Then `with_original()` adds the original text and the footer. This is the only post that quotes the email, because it has no summary.

### `with_original(top, content, settings) -> str`

Adds the original text in an expandable quote (`<blockquote expandable>`) and the footer. The result fits in `TELEGRAM_MAX_MESSAGE_CHARS`.

1. Computes the budget: the limit minus the top part, the quote tags and the footer.
2. When the escaped text is longer than the budget, cuts the text to the budget. Escaping makes the text longer, for example `&` becomes `&amp;`. So the function removes 50 more characters at a time until the escaped text and `…` fit.
3. When no text is left, returns the top part and the footer without a quote.

The function cuts the plain text before it escapes it. A cut in the middle of `&amp;` cannot happen.

### `call(method, payload, settings) -> dict`

Sends one Bot API request: `POST <TELEGRAM_BASE_URL>/bot<token>/<method>` with a JSON body. The timeout is `TELEGRAM_TIMEOUT_SECONDS`.

When the answer has `"ok": false`, it raises `TelegramError` with the method, the HTTP status and Telegram's description. The function builds this message itself: an `httpx` error contains the URL, and the URL contains the bot token. It returns the `result` field of the answer.

### `check(settings)`

Calls `getChat` with `TELEGRAM_CHAT_ID`. The call fails when the token is wrong, the chat id is wrong, or the bot is no longer in the group.

### `send_message(text, settings) -> int`

Calls `sendMessage` and returns the message id.

| Parameter | Value | Why |
|-----------|-------|-----|
| `chat_id` | `TELEGRAM_CHAT_ID` | The group |
| `text` | The formatted post | |
| `parse_mode` | `HTML` | Bold, italics and the quote |
| `link_preview_options` | `{"is_disabled": True}` | A link in the email does not create a preview card |

Every post is sent the same way, with a normal notification. The app does not send silent posts and does not pin posts.

### `send_summary()`, `send_original()`, `send_error()`

`send_summary()` and `send_original()` call the matching format function and `send_message()`. They return the message id for the log line.

`send_error(subject, error, settings)` posts `⚠️ Не удалось обработать письмо «subject»: error` (could not process the email). The error text is cut at `TELEGRAM_MAX_ERROR_CHARS` characters. `main.process()` writes the full error with its traceback to the log before the post.

## Constants, limits and flags

| Name | Value | Meaning |
|------|-------|---------|
| `URGENCY_LABEL` | `🔴 High`, `🟡 Medium`, `🟢 Low` | Urgency labels |
| `CATEGORY_LABEL` | `ℹ️ Информация`, `🎉 Мероприятие`, `✍️ Нужно действие`, `💰 Оплата`, `🔄 Изменение расписания`, `🩺 Здоровье`, `📌 Другое` | Category labels. One for each value of `summarize.Category` |
| `WEEKDAYS` | `пн` … `вс` | Monday first, as `date.weekday()` |
| `MONTHS` | `янв` … `дек` | Genitive case |
| `TELEGRAM_MAX_MESSAGE_CHARS` | Setting, 4096 | Length limit of a post |
| `TELEGRAM_TIMEOUT_SECONDS` | Setting, 30 | Timeout of one request |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_BASE_URL` | Settings | Bot API access |
| `TELEGRAM_MAX_ERROR_CHARS` | Setting, 500 | Length of the error text in `send_error()` |

## Errors and exit codes

| Situation | Result |
|-----------|--------|
| `check()` fails | Exception to `main.check_services()`. Exit code 1 |
| `send_summary()` or `send_original()` fails | Exception to `main.process()`. One failed attempt |
| `send_error()` fails | `main.process()` writes it to the log and still moves the email to `Failed` |

Possible exceptions: `TelegramError` for an answer with `"ok": false`, an `httpx` error for a network problem, a JSON error for an answer that is not JSON. None of their messages contain the bot token.

## Tests

`tests/test_telegram.py` covers:

- `ru_date()`;
- the post layout and the escaping of HTML characters;
- missing fields are left out of the post;
- a long original in the fallback post is cut to the limit;
- the fallback post keeps the original text;
- `check()` raises an error without the token in the message;
- `send_message()` returns the message id.
