import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


_requests = defaultdict(list)


def rate_limit(
    request: Request,
    max_requests: int = 60,
    window_seconds: int = 60,
):
    client_ip = request.client.host

    now = time.time()

    timestamps = _requests[client_ip]

    timestamps[:] = [
        timestamp
        for timestamp in timestamps
        if now - timestamp < window_seconds
    ]

    if len(timestamps) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )

    timestamps.append(now)