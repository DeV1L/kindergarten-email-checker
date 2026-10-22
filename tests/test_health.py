import urllib.error
import urllib.request

from kindergarten_email_checker import health


def get(server, path):
    try:
        return urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}{path}").status
    except urllib.error.HTTPError as error:
        return error.code


def test_readyz_only_after_the_start_check(monkeypatch):
    monkeypatch.setattr(health, "ready", False)
    server = health.start(port=0)
    try:
        assert get(server, "/readyz") == 503
        assert get(server, "/livez") == 200
        assert get(server, "/other") == 404
        monkeypatch.setattr(health, "ready", True)
        assert get(server, "/readyz") == 200
    finally:
        server.shutdown()
