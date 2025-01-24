from fastapi import APIRouter, HTTPException
from domain.services.training_service import TrainingService
from typing import Dict

router = APIRouter()

class TrainingController:
    def __init__(self):
        self.service = TrainingService()

    async def get_training_data(self, user_id: str):
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing 'id'")
        return await self.service.get_training_data(user_id)

controller = TrainingController()

@router.post("/training-data/fetch")
async def fetch_user_training_stats(request: Dict[str, str]):
    return await controller.get_training_data(request.get("id"))