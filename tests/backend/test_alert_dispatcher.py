"""Focused tests for bounded, secret-safe webhook HTTP requests."""

import hashlib
import json
from urllib.error import URLError

import pytest
from pydantic import SecretStr
from pydantic import ValidationError

from backend.core.config import Settings, settings
from backend.services import alert_dispatcher


class FakeResponse:
	status = 202

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		return False

	def read(self, size: int) -> bytes:
		return b""


def test_webhook_posts_json_with_hashed_idempotency_and_timeout(monkeypatch) -> None:
	requests = []

	class FakeOpener:
		def open(self, request, timeout):
			requests.append((request, timeout))
			return FakeResponse()

	monkeypatch.setattr(settings, "alert_webhook_url", SecretStr("https://receiver.example/alerts"))
	monkeypatch.setattr(settings, "alert_webhook_timeout_seconds", 7)
	monkeypatch.setattr(alert_dispatcher, "build_opener", lambda handler: FakeOpener())

	result = alert_dispatcher.send_alert_webhook({"event": {"magnitude": 4.2}}, "event:rule:source:id")

	assert result is None
	request, timeout = requests[0]
	assert request.get_method() == "POST"
	assert json.loads(request.data) == {"event": {"magnitude": 4.2}}
	assert request.get_header("Idempotency-key") == hashlib.sha256(b"event:rule:source:id").hexdigest()
	assert timeout == 7


def test_webhook_network_errors_do_not_expose_destination(monkeypatch) -> None:
	class FailingOpener:
		def open(self, request, timeout):
			raise URLError("https://private.example/path?token=secret")

	monkeypatch.setattr(settings, "alert_webhook_url", SecretStr("https://private.example/path?token=secret"))
	monkeypatch.setattr(alert_dispatcher, "build_opener", lambda handler: FailingOpener())

	result = alert_dispatcher.send_alert_webhook({}, "event:key")

	assert result == "network_error_URLError"
	assert "private.example" not in result
	assert "secret" not in result


@pytest.mark.parametrize(
	"url",
	[
		"http://hooks.example.com/alerts",
		"https://user:password@receiver.example/alerts",
		"https://receiver.example/alerts#fragment",
	],
)
def test_webhook_configuration_rejects_unsafe_destinations(url: str) -> None:
	with pytest.raises(ValidationError):
		Settings(_env_file=None, alert_webhook_url=url)


def test_webhook_configuration_requires_https_in_production_and_bounded_timeout() -> None:
	with pytest.raises(ValidationError):
		Settings(_env_file=None, app_environment="production", alert_webhook_url="http://localhost/hook")
	with pytest.raises(ValidationError, match="timeout"):
		Settings(_env_file=None, alert_webhook_timeout_seconds=31)
