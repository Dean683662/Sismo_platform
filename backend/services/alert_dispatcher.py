"""Bounded, secret-safe HTTP webhook delivery."""

import hashlib
from http.client import HTTPException as HTTPProtocolError
import json
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from backend.core.config import settings


class _NoRedirect(HTTPRedirectHandler):
	def redirect_request(self, request, response, code, message, headers, new_url):
		return None


def send_alert_webhook(payload: dict, idempotency_key: str) -> str | None:
	"""Return a safe error label on failure; never include the configured URL."""
	if settings.alert_webhook_url is None:
		return "webhook_not_configured"
	request = Request(
		settings.alert_webhook_url.get_secret_value(),
		data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
		headers={
			"Content-Type": "application/json",
			"Idempotency-Key": hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest(),
			"User-Agent": "SismoPlatform-AlertDispatcher/1.0",
		},
		method="POST",
	)
	try:
		with build_opener(_NoRedirect()).open(
			request,
			timeout=settings.alert_webhook_timeout_seconds,
		) as response:
			response.read(1)
			if not 200 <= response.status < 300:
				return f"http_status_{response.status}"
	except HTTPError as error:
		return f"http_status_{error.code}"
	except (URLError, TimeoutError, OSError, HTTPProtocolError) as error:
		return f"network_error_{type(error).__name__}"
	return None
