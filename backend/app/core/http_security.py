import time
from collections import deque
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

_API_PREFIX = "/api/v1/"
_RATE_LIMIT = 15
_WINDOW_SECONDS = 60.0
_hits_by_client: dict[str, deque[float]] = {}


def reset_rate_limit_state() -> None:
    _hits_by_client.clear()


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _add_security_headers(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


async def secure_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.method != "OPTIONS" and request.url.path.startswith(_API_PREFIX):
        now = time.monotonic()
        cutoff = now - _WINDOW_SECONDS
        key = _client_key(request)
        hits = _hits_by_client.setdefault(key, deque())
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= _RATE_LIMIT:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again shortly."},
            )
            response.headers["Retry-After"] = str(int(_WINDOW_SECONDS))
            return _add_security_headers(response)
        hits.append(now)

        # ponytail: this per-IP limiter is process-local; the one-instance course
        # demo keeps that sufficient without adding a shared rate-limit service.
        if len(_hits_by_client) > 2_048:
            stale = [
                client
                for client, client_hits in _hits_by_client.items()
                if not client_hits or client_hits[-1] <= cutoff
            ]
            for client in stale:
                _hits_by_client.pop(client, None)

    return _add_security_headers(await call_next(request))