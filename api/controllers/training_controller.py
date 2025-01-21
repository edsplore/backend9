from fastapi import APIRouter, HTTPException
from domain.services.training_service import TrainingService
from api.schemas.requests import TrainingDataRequest
from api.schemas.responses import TrainingDataResponse

router = APIRouter()

class TrainingController:
    def __init__(self):
        self.service = TrainingService()

    async def get_training_data(self, request: TrainingDataRequest) -> TrainingDataResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'id'")
        return await self.service.get_training_data(request.user_id)

controller = TrainingController()

@router.post("/training-data/fetch")
async def fetch_user_training_stats(request: dict) -> TrainingDataResponse:
    return await controller.get_training_data(TrainingDataRequest(user_id=request.get("id")))