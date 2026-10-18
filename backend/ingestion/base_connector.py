"""Contract shared by external seismic data connectors."""

from abc import ABC, abstractmethod


class ConnectorError(RuntimeError):
	"""Raised when a provider cannot return a usable response."""


class BaseConnector(ABC):
	provider_key: str
	records_skipped: int = 0

	@abstractmethod
	def fetch_events(self) -> list[dict]:
		"""Fetch raw provider records without persisting them."""