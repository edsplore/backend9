from typing import List
from domain.models.training import TrainingDataModel
from infrastructure.repositories.training_repository import TrainingRepository
from domain.interfaces.training_repository import ITrainingRepository

from utils.logger import Logger  # Ensure the import path is correct for your project

logger = Logger.get_logger(__name__)


class TrainingService:

    def __init__(self, repository: ITrainingRepository = None):
        self.repository = repository or TrainingRepository()
        logger.info("TrainingService initialized.")

    async def get_training_data(self, user_id: str) -> dict:
        logger.info("Fetching training data.")
        logger.debug(f"user_id={user_id}")

        try:
            training_plans = await self.repository.get_training_plans(user_id)
            stats = await self.repository.get_training_stats(user_id)
            logger.info(
                f"Fetched training plans and stats for user_id={user_id}.")
            return {"training_plans": training_plans, "stats": stats}
        except Exception as e:
            logger.error(
                f"Error fetching training data for user_id={user_id}: {str(e)}",
                exc_info=True)
            raise
