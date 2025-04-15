from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from utils.jwt_validator import JWTValidator
from utils.logger import Logger

logger = Logger.get_logger(__name__)


class JWTAuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for certain paths
        if request.url.path in ["/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        try:
            # Verify token and add payload to request state
            payload = await JWTValidator.verify_token(request)
            request.state.user = payload

            response = await call_next(request)
            return response

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}", exc_info=True)
            raise
