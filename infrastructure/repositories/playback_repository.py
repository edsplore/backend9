from typing import List, Optional
from domain.interfaces.playback_repository import IPlaybackRepository
from domain.models.playback import SimulationAttemptModel, AttemptAnalyticsModel
from infrastructure.database import Database

class PlaybackRepository(IPlaybackRepository):
    def __init__(self):
        self.db = Database()

    async def get_attempts(self, user_id: str) -> List[SimulationAttemptModel]:
        attempts_cursor = self.db.sim_attempts.find({"userId": user_id})
        return [await self._process_attempt(doc) async for doc in attempts_cursor]

    async def get_attempt_by_id(self, user_id: str, attempt_id: str) -> Optional[AttemptAnalyticsModel]:
        attempt_doc = await self.db.sim_attempts.find_one({
            "_id": attempt_id,
            "userId": user_id
        })
        return await self._process_attempt_analytics(attempt_doc) if attempt_doc else None

    async def _process_attempt(self, attempt_doc: dict) -> SimulationAttemptModel:
        # Implementation moved from service layer
        pass

    async def _process_attempt_analytics(self, attempt_doc: dict) -> AttemptAnalyticsModel:
        # Implementation moved from service layer
        pass