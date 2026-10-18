"""Bounded read-only API load probe for an isolated staging environment."""

import argparse
import http.cookiejar
import json
import math
import os
import statistics
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener


ENDPOINTS = (
	"/api/v1/dashboard/summary",
	"/api/v1/events?limit=50",
	"/api/v1/reports?limit=50",
)


def _login(base_url: str, email: str, password: str, timeout: float):
	opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
	body = json.dumps({"email": email, "password": password}).encode("utf-8")
	request = Request(
		f"{base_url}/api/v1/auth/login",
		data=body,
		headers={"Content-Type": "application/json"},
		method="POST",
	)
	with opener.open(request, timeout=timeout) as response:
		if response.status != 200:
			raise RuntimeError("Authentication failed")
		response.read()
	return opener


def _worker(base_url: str, email: str, password: str, deadline: float, timeout: float, results: list[float], errors: list[int], lock: threading.Lock) -> None:
	try:
		opener = _login(base_url, email, password, timeout)
	except (HTTPError, URLError, OSError, ValueError, RuntimeError):
		with lock:
			errors.append(1)
		return

	while time.monotonic() < deadline:
		for path in ENDPOINTS:
			if time.monotonic() >= deadline:
				return
			started = time.perf_counter()
			try:
				with opener.open(f"{base_url}{path}", timeout=timeout) as response:
					response.read()
					status_code = response.status
			except (HTTPError, URLError, OSError, TimeoutError):
				status_code = 0
			elapsed = time.perf_counter() - started
			with lock:
				results.append(elapsed)
				if status_code != 200:
					errors.append(1)


def _within_thresholds(p95_ms: float, error_rate: float, max_p95_ms: float, max_error_rate: float) -> bool:
	return p95_ms <= max_p95_ms and error_rate <= max_error_rate


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--base-url", default=os.environ.get("SISMO_LOAD_BASE_URL", "http://localhost:8000"))
	parser.add_argument("--workers", type=int, default=5)
	parser.add_argument("--seconds", type=int, default=30)
	parser.add_argument("--timeout", type=float, default=5)
	parser.add_argument("--max-p95-ms", type=float, default=2000)
	parser.add_argument("--max-error-rate", type=float, default=0.01)
	args = parser.parse_args()
	email = os.environ.get("SISMO_LOAD_EMAIL")
	password = os.environ.get("SISMO_LOAD_PASSWORD")
	parsed_url = urlparse(args.base_url)
	if not email or not password:
		parser.error("Set SISMO_LOAD_EMAIL and SISMO_LOAD_PASSWORD to a dedicated test account.")
	if parsed_url.scheme != "https" and parsed_url.hostname not in {"localhost", "127.0.0.1", "::1"}:
		parser.error("Use HTTPS for non-local targets.")
	if not 1 <= args.workers <= 100 or not 1 <= args.seconds <= 600 or not 0.1 <= args.timeout <= 60:
		parser.error("workers must be 1-100, seconds 1-600, and timeout 0.1-60.")
	if not math.isfinite(args.max_p95_ms) or args.max_p95_ms <= 0:
		parser.error("max-p95-ms must be a finite positive number.")
	if not math.isfinite(args.max_error_rate) or not 0 <= args.max_error_rate <= 1:
		parser.error("max-error-rate must be between 0 and 1.")

	results: list[float] = []
	errors: list[int] = []
	lock = threading.Lock()
	deadline = time.monotonic() + args.seconds
	threads = [
		threading.Thread(
			target=_worker,
			args=(args.base_url.rstrip("/"), email, password, deadline, args.timeout, results, errors, lock),
		)
		for _ in range(args.workers)
	]
	for thread in threads:
		thread.start()
	for thread in threads:
		thread.join()

	if not results:
		print(f"No successful HTTP samples; failed requests: {len(errors)}")
		return 1
	ordered = sorted(results)
	p95 = ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]
	error_rate = len(errors) / len(results)
	print(
		f"requests={len(results)} failures={len(errors)} "
		f"p50_ms={statistics.median(ordered) * 1000:.1f} p95_ms={p95 * 1000:.1f} "
		f"error_rate={error_rate:.4f} "
		f"workers={args.workers} duration_s={args.seconds}"
	)
	return int(not _within_thresholds(p95 * 1000, error_rate, args.max_p95_ms, args.max_error_rate))


if __name__ == "__main__":
	raise SystemExit(main())
