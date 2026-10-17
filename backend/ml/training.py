"""Reproducible baseline training for descriptive seismic experiments."""

from dataclasses import dataclass

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer

from backend.ml.evaluation import chronological_split, regression_metrics
from backend.ml.features import build_event_features
from backend.ml.preprocessing import prepare_event_dataset


@dataclass
class ExperimentResult:
	model: object
	metrics: dict[str, float]
	feature_names: list[str]
	target_name: str
	algorithm: str
	row_count: int
	train_period: tuple[str, str]
	evaluation_period: tuple[str, str]


def train_magnitude_baseline(records: list[dict], test_fraction: float = 0.2) -> ExperimentResult:
	"""Estimate reported magnitudes from event metadata for a temporal baseline."""
	frame = prepare_event_dataset(records)
	if len(frame) < 5:
		raise ValueError("At least five valid, unique events are required")

	features, target = build_event_features(frame)
	x_train, x_test, y_train, y_test = chronological_split(
		features, target, frame["occurred_at"], test_fraction
	)
	model = make_pipeline(SimpleImputer(strategy="median"), LinearRegression())
	model.fit(x_train, y_train)
	predicted = model.predict(x_test)

	train_times = frame.loc[x_train.index, "occurred_at"]
	evaluation_times = frame.loc[x_test.index, "occurred_at"]
	return ExperimentResult(
		model=model,
		metrics=regression_metrics(y_test, predicted),
		feature_names=list(features.columns),
		target_name="magnitude",
		algorithm="linear_regression",
		row_count=len(frame),
		train_period=(train_times.min().isoformat(), train_times.max().isoformat()),
		evaluation_period=(evaluation_times.min().isoformat(), evaluation_times.max().isoformat()),
	)