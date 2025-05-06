from fastapi import APIRouter, HTTPException
from domain.services.user_service import UserService
from api.schemas.requests import CreateUserRequest
from api.schemas.responses import CreateUserResponse
from utils.logger import Logger

logger = Logger.get_logger(__name__)

router = APIRouter()


class UserController:

    def __init__(self):
        self.service = UserService()
        logger.info("UserController initialized.")

    async def create_user(self,
                          request: CreateUserRequest) -> CreateUserResponse:
        logger.info("Received request to create a new user.")
        logger.debug(f"User Id: {request.user_id}")
        try:
            result = await self.service.create_user(request.user_id)
            logger.info(f"User created successfully: {result}")
            return result
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}", exc_info=True)
            raise


controller = UserController()


@router.post("/users/create", tags=["Users", "Create"])
async def create_user(request: CreateUserRequest) -> CreateUserResponse:
    """Create a new user"""
    return await controller.create_user(request)
