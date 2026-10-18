"""Normalize provider payloads to the platform event contract."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NormalizedSeismicEvent(BaseModel):
	model_config = ConfigDict(extra="forbid")

	external_id: str = Field(min_length=1, max_length=100)
	occurred_at: datetime
	latitude: float = Field(ge=-90, le=90)
	longitude: float = Field(ge=-180, le=180)
	magnitude: float = Field(ge=0, le=10)
	magnitude_type: str | None = Field(default=None, max_length=30)
	depth_km: float = Field(ge=0, le=1000)
	place: str = Field(min_length=1, max_length=300)
	source_url: str | None = Field(default=None, max_length=500)
	payload_hash: str = Field(min_length=64, max_length=64)


def _utc_datetime(value: Any) -> datetime:
	if isinstance(value, str):
		value = datetime.fromisoformat(value.replace("Z", "+00:00"))
	if not isinstance(value, datetime):
		raise ValueError("Event timestamp is missing or invalid")
	if value.tzinfo is None:
		return value.replace(tzinfo=timezone.utc)
	return value.astimezone(timezone.utc)


def normalize_igp_event(payload: dict[str, Any]) -> NormalizedSeismicEvent:
	occurred_at = _utc_datetime(payload.get("fecha_hora"))
	external_id = payload.get("codigo")
	if not external_id and payload.get("numero") is not None:
		external_id = f"{occurred_at:%Y%m%dT%H%M%S}-{payload['numero']}"
	canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
	return NormalizedSeismicEvent(
		external_id=str(external_id or ""),
		occurred_at=occurred_at,
		latitude=payload.get("latitud"),
		longitude=payload.get("longitud"),
		magnitude=payload.get("magnitud"),
		magnitude_type=payload.get("tipo_magnitud"),
		depth_km=payload.get("profundidad"),
		place=payload.get("referencia") or payload.get("superficie") or "Ubicación no especificada",
		source_url=payload.get("source_url") or payload.get("mapa_sismico_url") or "https://ultimosismo.igp.gob.pe/ultimo-sismo",
		payload_hash=hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest(),
	)