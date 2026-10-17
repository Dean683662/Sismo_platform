"""Chronological validation and metrics for seismic event experiments."""

import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def chronological_split(
	features: pd.DataFrame,
	target: pd.Series,
	timestamps: pd.Series,
	test_fraction: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
	if not 0 < test_fraction < 1:
		raise ValueError("test_fraction must be between 0 and 1")
	if len(features) != len(target) or len(target) != len(timestamps):
		raise ValueError("Features, target, and timestamps must have equal lengths")
	if len(features) < 5:
		raise ValueError("At least five valid events are required")

	order = timestamps.sort_values(kind="stable").index
	split_at = max(1, min(len(order) - 1, int(len(order) * (1 - test_fraction))))
	train_index, test_index = order[:split_at], order[split_at:]
	return features.loc[train_index], features.loc[test_index], target.loc[train_index], target.loc[test_index]


def regression_metrics(actual: pd.Series, predicted) -> dict[str, float]:
	return {
		"mae": float(mean_absolute_error(actual, predicted)),
		"rmse": float(mean_squared_error(actual, predicted) ** 0.5),
		"r2": float(r2_score(actual, predicted)),
	}