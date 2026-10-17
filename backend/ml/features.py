"""Features for clearly scoped experiments on already reported events."""

import pandas as pd


EVENT_FEATURES = ("latitude", "longitude", "depth_km")
EVENT_TARGET = "magnitude"


def build_event_features(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
	"""Build a regression matrix; observed magnitude is the target, not a feature."""
	missing = set((*EVENT_FEATURES, EVENT_TARGET)).difference(frame.columns)
	if missing:
		raise ValueError(f"Missing feature fields: {', '.join(sorted(missing))}")
	return frame.loc[:, EVENT_FEATURES].astype(float), frame[EVENT_TARGET].astype(float)