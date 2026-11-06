import time
from collections import defaultdict
from threading import Lock
from typing import Optional
from fastapi import Request, HTTPException, status


class InMemoryRateLimiter:
    """
    Sliding window rate limiter for public endpoints.
    Tracks request timestamps per IP address.
    """

    def __init__(self):
        self._requests = defaultdict(list)
        self._lock = Lock()

    def get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def check_rate_limit(
        self,
        request: Request,
        action: str,
        max_requests: int,
        window_seconds: int = 60,
    ) -> None:
        client_ip = self.get_client_ip(request)
        key = f"{action}:{client_ip}"
        now = time.time()

        with self._lock:
            timestamps = self._requests[key]
            cutoff = now - window_seconds
            valid_timestamps = [t for t in timestamps if t > cutoff]

            if len(valid_timestamps) >= max_requests:
                retry_after = max(1, int(valid_timestamps[0] + window_seconds - now) + 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "RATE_LIMIT_EXCEEDED",
                        "message": f"Too many requests for {action}. Please wait {retry_after} seconds before trying again.",
                        "retry_after_seconds": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            valid_timestamps.append(now)
            self._requests[key] = valid_timestamps

    def reset(self) -> None:
        """Resets the rate limiter (useful for unit tests)."""
        with self._lock:
            self._requests.clear()


rate_limiter = InMemoryRateLimiter()
