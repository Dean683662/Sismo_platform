"""Tests for the machine learning pipeline."""

from datetime import datetime, timedelta, timezone

import pytest

from backend.ml.preprocessing import prepare_event_dataset
from backend.ml.training import train_magnitude_baseline


def event_records(count: int = 20) -> list[dict]:
	start = datetime(2026, 1, 1, tzinfo=timezone.utc)
	return [
		{
			"external_id": f"event-{index}",
			"source_id": "igp",
			"occurred_at": start + timedelta(days=index),
			"latitude": -10 + index / 10,
			"longitude": -75 + index / 20,
			"magnitude": 2 + index / 10,
			"depth_km": 5 + index,
		}
		for index in range(count)
	]


def test_prepare_event_dataset_deduplicates_and_rejects_invalid_ranges() -> None:
	records = event_records(6)
	records.append(records[0].copy())
	records.append({**records[1], "external_id": "invalid", "latitude": 100})

	prepared = prepare_event_dataset(records)

	assert len(prepared) == 6
	assert prepared["occurred_at"].is_monotonic_increasing


def test_baseline_uses_chronological_holdout_and_reports_regression_metrics() -> None:
	result = train_magnitude_baseline(event_records())

	assert result.algorithm == "linear_regression"
	assert result.target_name == "magnitude"
	assert result.feature_names == ["latitude", "longitude", "depth_km"]
	assert result.evaluation_period[0] > result.train_period[1]
	assert set(result.metrics) == {"mae", "rmse", "r2"}
	assert result.metrics["rmse"] < 0.01


def test_baseline_requires_enough_unique_valid_events() -> None:
	with pytest.raises(ValueError, match="five valid"):
		train_magnitude_baseline(event_records(4))