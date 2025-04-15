import jwt
from fastapi import HTTPException, Request
from functools import wraps
from utils.logger import Logger

logger = Logger.get_logger(__name__)


class JWTValidator:
    _instance = None
    _public_key = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._initialize_public_key()
        return cls._instance

    @classmethod
    def _initialize_public_key(cls):
        """Initialize with public key"""
        try:
            with open("public.pem", "r") as key_file:
                cls._public_key = key_file.read()
            logger.info("JWT public key loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load public key: {str(e)}", exc_info=True)
            raise

    @classmethod
    async def verify_token(cls, request: Request) -> dict:
        """Verify JWT token from request header"""
        try:
            if cls._public_key is None:
                cls._initialize_public_key()

            auth_header = request.headers.get('Authorization')
            if not auth_header:
                logger.warning("No Authorization header found")
                raise HTTPException(status_code=401,
                                    detail="No authorization token provided")

            try:
                scheme, token = auth_header.split()
                if scheme.lower() != 'bearer':
                    logger.warning("Invalid authentication scheme")
                    raise HTTPException(status_code=401,
                                        detail="Invalid authentication scheme")
            except ValueError:
                logger.warning("Invalid Authorization header format")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authorization header format")

            try:
                payload = jwt.decode(token,
                                     cls._public_key,
                                     algorithms=['RS256'])
                logger.debug(
                    f"Token verified successfully for user: {payload.get('sub')}"
                )
                return payload
            except jwt.ExpiredSignatureError:
                logger.warning("Token has expired")
                raise HTTPException(status_code=401,
                                    detail="Token has expired")
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid token: {str(e)}")
                raise HTTPException(status_code=401, detail="Invalid token")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500,
                                detail="Error processing authentication token")
