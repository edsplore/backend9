from abc import ABC, abstractmethod
from typing import List, Dict
from domain.models.training import TrainingDataModel

class ITrainingRepository(ABC):
    @abstractmethod
    async def get_training_plans(self, user_id: str) -> List[TrainingDataModel]:
        pass

    @abstractmethod
    async def get_training_stats(self, user_id: str) -> Dict:
        pass