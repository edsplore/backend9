from fastapi import APIRouter, HTTPException
from services.training_data_service import TrainingDataService
from models.training_data import TrainingDataResponse

router = APIRouter()

@router.post("/training-data/fetch")
async def fetch_user_training_stats(request: dict) -> TrainingDataResponse:
    user_id = request.get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing 'id'")

    service = TrainingDataService()
    return await service.get_training_data(user_id)