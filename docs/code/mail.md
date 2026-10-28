# mail.py

Source: [src/kindergarten_email_checker/mail.py](../../src/kindergarten_email_checker/mail.py)

## Purpose

`mail.py` is the IMAP access to the dedicated mailbox. It connects, fetches the unseen emails, moves emails between labels and logs out. It uses the library `imap-tools`. The module holds no state. The mailbox is the state:

- unseen email with the inbox label is the queue;
- a move to `Processed`, `Ignored` or `Failed` is the commit;
- the fetch does not set the Seen flag.

## Who runs it

| Caller | Functions |
|--------|-----------|
| `main.check_services()` | `connect()`, `close()`, once at start |
| `main.poll()` | `connect()`, `fetch_unseen()`, `close()`, once in each poll |
| `main.process()` | `move()`, once for each email |

Each poll opens a new connection and closes it at the end. The app does not keep a connection open between polls and does not use IMAP IDLE. [ARCHITECTURE.md](../ARCHITECTURE.md#runtime-loop) explains why.

## Layout

| Item | Kind |
|------|------|
| Module docstring | The state model in short |
| `connect()` | Function |
| `refresh_capabilities()` | Function |
| `ensure_labels()` | Function |
| `close()` | Function |
| `fetch_unseen()` | Function |
| `move()` | Function |

The module has no class. `imap_tools.MailBox` is the connection object. Each function takes it as the first argument.

### `connect(settings) -> MailBox`

1. Opens an SSL connection to `IMAP_HOST`, port 993, with the socket timeout `IMAP_TIMEOUT_SECONDS`.
2. Logs in with `IMAP_USER` and `IMAP_PASSWORD` and selects the inbox label (`IMAP_FOLDER_INBOX`).
3. Calls `refresh_capabilities()`.
4. Calls `ensure_labels()` for `Processed`, `Ignored` and `Failed`.
5. Returns the `MailBox`.

### `refresh_capabilities(mailbox)`

Sends the IMAP command `CAPABILITY` again after login and stores the answer in `mailbox.client.capabilities`. Gmail lists the `MOVE` capability only after login. `imap-tools` keeps the list from before login. Without the new list, `imap-tools` moves an email by copy and delete. With some Gmail settings, the delete sends the email to Trash.

### `ensure_labels(mailbox, labels)`

Creates each label that does not exist. In Gmail, an IMAP folder is a label. The function runs in each poll, so a label that the owner deletes comes back.

### `close(mailbox)`

Logs out. It ignores every error, because after a dropped connection the logout fails too. `main.poll()` calls it in `finally`.

### `fetch_unseen(mailbox) -> list[MailMessage]`

Fetches every email without the Seen flag in the selected label.

| Argument | Value | Why |
|----------|-------|-----|
| Search | `AND(seen=False)` | Only unseen emails are the queue |
| `mark_seen` | `False` | The fetch does not change the state |
| `bulk` | `True` | One `FETCH` command for all emails, not one for each email |

The function returns a list, not a generator. All unseen emails, with their attachments, are in memory at the same time.

CAUTION: when the owner opens an email of the inbox label in the Gmail web interface, Gmail sets the Seen flag. The app then skips this email, and it stays in the inbox label. To process it again, mark it as unread in Gmail.

### `move(mailbox, uids, folder)`

Moves the emails with these UIDs to the label `folder`. With the `MOVE` capability, this is one IMAP `MOVE` command: Gmail removes the inbox label and adds the new label. This is the commit step for every outcome.

## Constants, limits and flags

| Name | Source | Meaning |
|------|--------|---------|
| `IMAP_HOST` | Setting | IMAP server, port 993 with SSL |
| `IMAP_USER`, `IMAP_PASSWORD` | Settings | Login of the dedicated mailbox |
| `IMAP_FOLDER_INBOX` | Setting | The label that `connect()` selects |
| `IMAP_FOLDER_PROCESSED`, `IMAP_FOLDER_IGNORED`, `IMAP_FOLDER_FAILED` | Settings | The labels that `ensure_labels()` creates |
| `IMAP_TIMEOUT_SECONDS` | Setting | Socket timeout. A stalled connection cannot block the loop |

## Errors and exit codes

The module catches errors only in `close()`. Every other IMAP error goes to the caller:

| Caller | Result of an IMAP error |
|--------|-------------------------|
| `main.check_services()` | Exit code 1 |
| `main.poll()` | The poll ends. The next poll tries again |

A wrong app password raises `imap_tools.errors.MailboxLoginError`.

## Tests

`tests/test_mail.py` uses a fake `MailBox`. It covers:

- `ensure_labels()` creates only the missing labels;
- `refresh_capabilities()` picks up `MOVE` from the answer after login.
