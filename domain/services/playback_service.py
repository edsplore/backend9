from typing import List, Optional
from domain.models.playback import SimulationAttemptModel, AttemptAnalyticsModel
from infrastructure.repositories.playback_repository import PlaybackRepository
from domain.interfaces.playback_repository import IPlaybackRepository

from utils.logger import Logger  # Adjust import path if needed

logger = Logger.get_logger(__name__)


class PlaybackService:

    def __init__(self, repository: IPlaybackRepository = None):
        self.repository = repository or PlaybackRepository()
        logger.info("PlaybackService initialized.")

    async def get_attempts(self, user_id: str) -> List[SimulationAttemptModel]:
        logger.info("Fetching attempts.")
        logger.debug(f"user_id={user_id}")
        return await self.repository.get_attempts(user_id)

    async def get_attempt_by_id(
            self, user_id: str,
            attempt_id: str) -> Optional[AttemptAnalyticsModel]:
        logger.info("Fetching attempt by ID.")
        logger.debug(f"user_id={user_id}, attempt_id={attempt_id}")
        return await self.repository.get_attempt_by_id(user_id, attempt_id)
