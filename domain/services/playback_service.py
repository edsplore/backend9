from typing import List, Optional
from domain.models.playback import SimulationAttemptModel, AttemptAnalyticsModel
from infrastructure.repositories.playback_repository import PlaybackRepository
from domain.interfaces.playback_repository import IPlaybackRepository

class PlaybackService:
    def __init__(self, repository: IPlaybackRepository = None):
        self.repository = repository or PlaybackRepository()

    async def get_attempts(self, user_id: str) -> List[SimulationAttemptModel]:
        return await self.repository.get_attempts(user_id)

    async def get_attempt_by_id(self, user_id: str, attempt_id: str) -> Optional[AttemptAnalyticsModel]:
        return await self.repository.get_attempt_by_id(user_id, attempt_id)