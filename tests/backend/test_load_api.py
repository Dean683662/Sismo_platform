from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


_spec = spec_from_file_location("sismo_load_api", Path(__file__).resolve().parents[1] / "load_api.py")
assert _spec is not None and _spec.loader is not None
_load_api = module_from_spec(_spec)
_spec.loader.exec_module(_load_api)


@pytest.mark.parametrize(
	("p95_ms", "error_rate", "max_p95_ms", "max_error_rate", "expected"),
	[
		(1500, 0.01, 2000, 0.01, True),
		(2000, 0, 2000, 0.01, True),
		(2001, 0, 2000, 0.01, False),
		(1000, 0.011, 2000, 0.01, False),
	],
)
def test_load_probe_enforces_configured_acceptance_thresholds(
	p95_ms: float,
	error_rate: float,
	max_p95_ms: float,
	max_error_rate: float,
	expected: bool,
) -> None:
	assert _load_api._within_thresholds(p95_ms, error_rate, max_p95_ms, max_error_rate) is expected
