"""Tests for the machine learning pipeline."""

from datetime import datetime, timedelta, timezone

import pytest

from backend.ml.preprocessing import prepare_event_dataset
from backend.ml.training import train_magnitude_baseline, train_magnitude_classification_baseline


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
	assert {"mae", "rmse", "r2", "mean_baseline_mae", "mean_baseline_rmse", "mean_baseline_r2"} == set(result.metrics)
	assert result.metrics["rmse"] < 0.01
	assert result.metrics["rmse"] < result.metrics["mean_baseline_rmse"]


def test_classification_compares_reported_magnitude_bands_and_returns_confusion_matrix() -> None:
	records = event_records(30)
	for index, record in enumerate(records):
		record["magnitude"] = [3.0, 4.5, 5.5][index % 3]

	result = train_magnitude_classification_baseline(records)

	assert result.target_name == "reported_magnitude_band"
	assert result.algorithm == "logistic_regression"
	assert result.evaluation_period[0] > result.train_period[1]
	assert result.validation_details["class_labels"] == ["low", "moderate", "high"]
	assert len(result.validation_details["confusion_matrix"]) == 3
	assert set(result.metrics) == {
		"accuracy", "precision_macro", "recall_macro", "f1_macro",
		"baseline_accuracy", "baseline_precision_macro", "baseline_recall_macro", "baseline_f1_macro",
	}


def test_baseline_requires_enough_unique_valid_events() -> None:
	with pytest.raises(ValueError, match="five valid"):
		train_magnitude_baseline(event_records(4))