from abc import ABC, abstractmethod
from typing import List, Optional
from domain.models.playback import SimulationAttemptModel, AttemptAnalyticsModel

class IPlaybackRepository(ABC):
    @abstractmethod
    async def get_attempts(self, user_id: str) -> List[SimulationAttemptModel]:
        pass

    @abstractmethod
    async def get_attempt_by_id(self, user_id: str, attempt_id: str) -> Optional[AttemptAnalyticsModel]:
        pass