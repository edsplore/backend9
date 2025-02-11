from typing import List
from domain.models.training import TrainingDataModel
from infrastructure.repositories.training_repository import TrainingRepository
from domain.interfaces.training_repository import ITrainingRepository

class TrainingService:
    def __init__(self, repository: ITrainingRepository = None):
        self.repository = repository or TrainingRepository()

    async def get_training_data(self, user_id: str) -> List[TrainingDataModel]:
        training_plans = await self.repository.get_training_plans(user_id)
        stats = await self.repository.get_training_stats(user_id)
        return {"training_plans": training_plans, "stats": stats}