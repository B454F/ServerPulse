
import os

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


ALLOWED_ORIGINS = set(
    os.getenv(
        "ALLOWED_ORIGINS",
        "https://localhost"
    ).split(",")
)


class SecurityMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        if request.url.path.startswith("/api/"):

            if request.method not in (
                "GET", "HEAD", "OPTIONS"
            ):

                origin = request.headers.get("origin")

                if origin and origin not in ALLOWED_ORIGINS:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": "Origin not allowed"
                        }
                    )

                if request.cookies.get("serverpulse_session"):

                    if origin not in ALLOWED_ORIGINS:
                        return JSONResponse(
                            status_code=403,
                            content={
                                "detail": "Invalid request origin"
                            }
                        )

        response = await call_next(request)

        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"

        return response
