from kindergarten_email_checker.mail import ensure_labels, refresh_capabilities


class FakeFolders:
    def __init__(self, existing):
        self.names = set(existing)
        self.created = []

    def exists(self, name):
        return name in self.names

    def create(self, name):
        self.created.append(name)
        self.names.add(name)


class FakeClient:
    capabilities = ("IMAP4REV1", "IDLE")

    def capability(self):
        return "OK", [b"IMAP4rev1 IDLE MOVE UIDPLUS"]


class FakeMailbox:
    def __init__(self, existing=()):
        self.folder = FakeFolders(existing)
        self.client = FakeClient()


def test_ensure_labels_creates_only_missing():
    mailbox = FakeMailbox(existing=["Processed"])
    ensure_labels(mailbox, ["Processed", "Ignored", "Failed"])
    assert mailbox.folder.created == ["Ignored", "Failed"]


def test_refresh_capabilities_picks_up_move():
    mailbox = FakeMailbox()
    refresh_capabilities(mailbox)
    assert "MOVE" in mailbox.client.capabilities
