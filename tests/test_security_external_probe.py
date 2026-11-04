"""The external security smoke test never sends authentication or mutates state."""

from urllib.error import HTTPError, URLError

import pytest

from scripts import security_probe


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_probe_only_issues_four_read_only_requests_and_requires_expected_codes(monkeypatch):
    calls = []

    def read(request, timeout):
        calls.append((request.full_url, request.get_method(), timeout))
        if request.full_url.endswith("/health"):
            return FakeResponse()
        if request.full_url.endswith("/api/v1/knowledge"):
            raise HTTPError(request.full_url, 401, "Unauthorized", {}, None)
        raise HTTPError(request.full_url, 404, "Not found", {}, None)

    monkeypatch.setattr(security_probe, "urlopen", read)
    assert security_probe.probe("https://secure.example.test") == []
    assert len(calls) == 4
    assert {method for _, method, _ in calls} == {"GET"}
    assert all("X-API-Key" not in url for url, _, _ in calls)


def test_probe_reports_api_still_open(monkeypatch):
    def read(request, timeout):
        return FakeResponse()

    monkeypatch.setattr(security_probe, "urlopen", read)
    findings = security_probe.probe("https://open.example.test")
    assert any("/api/v1/knowledge" in item and "HTTP 200" in item for item in findings)
    assert any("/openapi.json" in item and "HTTP 200" in item for item in findings)


@pytest.mark.parametrize("bad_url", [
    "http://example.com",
    "https://user:pass@example.com",
    "file:///etc/passwd",
    "https://example.com/api/v1/knowledge",
    "https://example.com?key=secret",
])
def test_probe_refuses_untrusted_targets(bad_url):
    with pytest.raises(ValueError, match="HTTPS"):
        security_probe.probe(bad_url)


def test_probe_reports_unreachable_server_without_retry(monkeypatch):
    calls = []

    def fails(request, timeout):
        calls.append(request.full_url)
        raise URLError("offline")

    monkeypatch.setattr(security_probe, "urlopen", fails)
    findings = security_probe.probe("https://offline.example.test")
    assert len(findings) == 4
    assert len(calls) == 4
    assert all("no se pudo conectar" in item for item in findings)
