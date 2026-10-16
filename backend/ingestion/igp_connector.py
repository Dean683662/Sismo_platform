"""Client for the public IGP latest-event JSON endpoint."""

import httpx

from backend.core.config import settings
from backend.ingestion.base_connector import BaseConnector, ConnectorError


class IGPConnector(BaseConnector):
	provider_key = "igp"

	def __init__(
		self,
		endpoint: str | None = None,
		timeout_seconds: float = 15,
		transport: httpx.BaseTransport | None = None,
	) -> None:
		self.endpoint = endpoint or settings.igp_latest_event_url
		self.timeout_seconds = timeout_seconds
		self.transport = transport

	def fetch_events(self) -> list[dict]:
		try:
			with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True, transport=self.transport) as client:
				response = client.get(self.endpoint, headers={"Accept": "application/json", "User-Agent": "SismoPlatform/0.1"})
				response.raise_for_status()
				payload = response.json()
		except (httpx.HTTPError, ValueError) as error:
			raise ConnectorError("IGP latest-event service is unavailable or returned invalid JSON") from error

		if isinstance(payload, dict) and isinstance(payload.get("data"), list):
			records = payload["data"]
		elif isinstance(payload, list):
			records = payload
		elif isinstance(payload, dict):
			records = [payload]
		else:
			raise ConnectorError("IGP response has an unsupported structure")

		return [
			record
			for record in records
			if isinstance(record, dict) and record.get("simulacro") in (None, False, 0, "", "0", "false", "False")
		]