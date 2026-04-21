"""FastAPI middleware that validates JWT tokens.

If a request includes an ``Authorization: Bearer <token>`` header, the token is
validated and the ``request.state.user`` attribute is populated with the user
email (``sub`` claim).  Requests without a token are allowed to continue – it is
up to the individual endpoint to enforce authentication (e.g., via the
``get_current_user`` dependency in ``router.py``).
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .utils import decode_access_token


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header: str | None = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            payload = decode_access_token(token)
            if payload and "sub" in payload:
                # Attach user identifier to request state for downstream use
                request.state.user = payload["sub"]
        # Continue processing the request (protected endpoints will still
        # raise 401 if the dependency is used)
        response: Response = await call_next(request)
        return response
