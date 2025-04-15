from fastapi import APIRouter, HTTPException
from domain.services.training_service import TrainingService
from typing import Dict
from utils.logger import Logger

logger = Logger.get_logger(__name__)
router = APIRouter()


class TrainingController:
    def __init__(self):
        self.service = TrainingService()
        logger.info("TrainingController initialized.")

    async def get_training_data(self, user_id: str):
        logger.info("Received request to fetch training data.")
        logger.debug(f"user_id: {user_id}")

        try:

            data = await self.service.get_training_data(user_id)
            logger.info(f"Training data fetched successfully for user_id: {user_id}")
            return data
        except Exception as e:
            logger.error(f"Error fetching training data: {str(e)}", exc_info=True)
            raise


controller = TrainingController()

@router.post("/training-data/fetch", tags=["Training", "Read"])
async def fetch_user_training_stats(request: Dict[str, str]):
    user_id = request.get("id")
    logger.info("API endpoint called: /training-data/fetch")
    logger.debug(f"Request body: {request}")
    return await controller.get_training_data(user_id)
