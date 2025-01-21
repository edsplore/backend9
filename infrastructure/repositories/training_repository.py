from typing import List, Dict, Set
from domain.interfaces.training_repository import ITrainingRepository
from domain.models.training import TrainingDataModel
from infrastructure.database import Database

class TrainingRepository(ITrainingRepository):
    def __init__(self):
        self.db = Database()

    async def get_training_plans(self, user_id: str) -> List[TrainingDataModel]:
        training_plan_ids = await self._get_user_assignments(user_id)
        return await self._build_training_plans(user_id, training_plan_ids)

    async def get_training_stats(self, user_id: str) -> Dict:
        # Implementation moved from service layer
        pass

    async def _get_user_assignments(self, user_id: str) -> Set[str]:
        # Implementation moved from service layer
        pass

    async def _build_training_plans(self, user_id: str, training_plan_ids: Set[str]) -> List[TrainingDataModel]:
        # Implementation moved from service layer
        pass