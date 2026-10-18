"""Reproducible baseline training for descriptive seismic experiments."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
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
	validation_details: dict


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
	baseline = DummyRegressor(strategy="mean")
	baseline.fit(x_train, y_train)
	baseline_metrics = regression_metrics(y_test, baseline.predict(x_test))

	train_times = frame.loc[x_train.index, "occurred_at"]
	evaluation_times = frame.loc[x_test.index, "occurred_at"]
	return ExperimentResult(
		model=model,
		metrics={
			**regression_metrics(y_test, predicted),
			**{f"mean_baseline_{name}": value for name, value in baseline_metrics.items()},
		},
		feature_names=list(features.columns),
		target_name="magnitude",
		algorithm="linear_regression",
		row_count=len(frame),
		train_period=(train_times.min().isoformat(), train_times.max().isoformat()),
		evaluation_period=(evaluation_times.min().isoformat(), evaluation_times.max().isoformat()),
		validation_details={},
	)


def train_magnitude_classification_baseline(
	records: list[dict],
	test_fraction: float = 0.2,
) -> ExperimentResult:
	"""Classify already-reported magnitudes into descriptive, non-predictive bands."""
	frame = prepare_event_dataset(records)
	if len(frame) < 10:
		raise ValueError("At least ten valid events are required for classification")
	features, _ = build_event_features(frame)
	target = pd.cut(
		frame["magnitude"],
		bins=[-np.inf, 4, 5, np.inf],
		labels=["low", "moderate", "high"],
		right=False,
	)
	x_train, x_test, y_train, y_test = chronological_split(
		features, target, frame["occurred_at"], test_fraction
	)
	classes = list(target.cat.categories)
	training_counts = y_train.value_counts()
	missing_training_classes = [category for category in classes if training_counts.get(category, 0) < 2]
	if missing_training_classes:
		raise ValueError(
			"Chronological training data must contain at least two examples from each magnitude band; "
			"widen the dataset period or adjust the evaluation fraction"
		)

	model = make_pipeline(
		SimpleImputer(strategy="median"),
		LogisticRegression(max_iter=1000, random_state=42),
	)
	model.fit(x_train, y_train)
	predicted = model.predict(x_test)
	baseline = DummyClassifier(strategy="most_frequent")
	baseline.fit(x_train, y_train)
	baseline_predicted = baseline.predict(x_test)
	metrics = {
		"accuracy": float(accuracy_score(y_test, predicted)),
		"precision_macro": float(precision_score(y_test, predicted, average="macro", zero_division=0)),
		"recall_macro": float(recall_score(y_test, predicted, average="macro", zero_division=0)),
		"f1_macro": float(f1_score(y_test, predicted, average="macro", zero_division=0)),
		"baseline_accuracy": float(accuracy_score(y_test, baseline_predicted)),
		"baseline_precision_macro": float(
			precision_score(y_test, baseline_predicted, average="macro", zero_division=0)
		),
		"baseline_recall_macro": float(
			recall_score(y_test, baseline_predicted, average="macro", zero_division=0)
		),
		"baseline_f1_macro": float(
			f1_score(y_test, baseline_predicted, average="macro", zero_division=0)
		),
	}
	train_times = frame.loc[x_train.index, "occurred_at"]
	evaluation_times = frame.loc[x_test.index, "occurred_at"]
	matrix = confusion_matrix(y_test, predicted, labels=classes)
	return ExperimentResult(
		model=model,
		metrics=metrics,
		feature_names=list(features.columns),
		target_name="reported_magnitude_band",
		algorithm="logistic_regression",
		row_count=len(frame),
		train_period=(train_times.min().isoformat(), train_times.max().isoformat()),
		evaluation_period=(evaluation_times.min().isoformat(), evaluation_times.max().isoformat()),
		validation_details={
			"class_labels": classes,
			"confusion_matrix": matrix.tolist(),
			"training_class_counts": {str(key): int(value) for key, value in training_counts.items()},
		},
	)