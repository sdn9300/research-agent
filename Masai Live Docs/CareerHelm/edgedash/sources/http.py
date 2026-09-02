"""
EdgeDash Subsystem 3: HTTP Client Helper
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 3 (10s timeout, retries, rate-limiting)
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional
import requests

_LAST_REQUEST_TIME = 0.0
_MIN_REQUEST_INTERVAL = 1.0  # 1 req / sec rate limit


def get_json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 10.0,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """Perform rate-limited, retried HTTP GET request returning parsed JSON."""
    global _LAST_REQUEST_TIME

    # Enforce rate-limiting
    elapsed = time.time() - _LAST_REQUEST_TIME
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)

    default_headers = {
        "User-Agent": "EdgeDash-JobRadar/1.0 (+https://github.com/sdn9300/EdgeDash)",
        "Accept": "application/json",
    }
    if headers:
        default_headers.update(headers)

    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            _LAST_REQUEST_TIME = time.time()
            resp = requests.get(url, params=params, headers=default_headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as err:
            last_err = err
            if attempt < max_retries:
                backoff_sec = (attempt + 1) * 1.5
                time.sleep(backoff_sec)
            else:
                break

    raise RuntimeError(f"HTTP GET failed after {max_retries + 1} attempts for '{url}': {last_err}") from last_err
