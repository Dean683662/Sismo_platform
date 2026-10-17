"""Clean and validate normalized seismic event records for experiments."""

import pandas as pd


EVENT_COLUMNS = (
	"external_id",
	"source_id",
	"occurred_at",
	"latitude",
	"longitude",
	"magnitude",
	"depth_km",
)


def prepare_event_dataset(records: list[dict]) -> pd.DataFrame:
	"""Return valid, deduplicated events ordered by occurrence time."""
	if not records:
		return pd.DataFrame(columns=EVENT_COLUMNS)

	frame = pd.DataFrame.from_records(records)
	missing = set(EVENT_COLUMNS).difference(frame.columns)
	if missing:
		raise ValueError(f"Missing required event fields: {', '.join(sorted(missing))}")

	frame = frame.loc[:, EVENT_COLUMNS].copy()
	frame["occurred_at"] = pd.to_datetime(frame["occurred_at"], utc=True, errors="coerce")
	for column in ("latitude", "longitude", "magnitude", "depth_km"):
		frame[column] = pd.to_numeric(frame[column], errors="coerce")

	valid = (
		frame["occurred_at"].notna()
		& frame["latitude"].between(-90, 90)
		& frame["longitude"].between(-180, 180)
		& frame["magnitude"].between(0, 10)
		& frame["depth_km"].between(0, 1000)
		& frame["external_id"].notna()
		& frame["source_id"].notna()
	)
	frame = frame.loc[valid].drop_duplicates(["source_id", "external_id"], keep="last")
	return frame.sort_values(["occurred_at", "source_id", "external_id"]).reset_index(drop=True)