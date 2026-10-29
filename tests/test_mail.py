from kindergarten_email_checker.mail import refresh_capabilities


class FakeClient:
    capabilities = ("IMAP4REV1", "IDLE")

    def capability(self):
        return "OK", [b"IMAP4rev1 IDLE MOVE UIDPLUS"]


class FakeMailbox:
    client = FakeClient()


def test_refresh_capabilities_picks_up_move():
    mailbox = FakeMailbox()
    refresh_capabilities(mailbox)
    assert "MOVE" in mailbox.client.capabilities
