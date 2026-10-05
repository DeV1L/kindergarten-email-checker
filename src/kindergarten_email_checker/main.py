"""Process entry point and the main loop.

Loop (docs/ARCHITECTURE.md, section 4):
connect, ensure the state labels exist, sweep once, then forever:
IDLE wait up to SWEEP_MINUTES, process every unseen message, repeat.
"""

from __future__ import annotations

import logging
import sys

from kindergarten_email_checker import __version__
from kindergarten_email_checker.config import Settings

log = logging.getLogger("kindergarten_email_checker")


def run() -> int:
    """Console entry point. Returns the process exit code."""
    settings = Settings()  # fails with a readable message when a required variable is missing
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    log.info(
        "kindergarten-email-checker %s starting: mailbox=%s model=%s sweep=%s min",
        __version__,
        settings.imap_user,
        settings.llm_model,
        settings.sweep_minutes,
    )
    return loop(settings)


def loop(settings: Settings) -> int:
    """Wake, fetch unseen, process each message, move it. Implementation pending."""
    raise NotImplementedError("Processing loop not implemented yet. See docs/ARCHITECTURE.md.")
