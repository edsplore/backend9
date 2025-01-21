from fastapi import APIRouter, HTTPException
from typing import Dict, List
from services.playback_data_service import PlaybackDataService
from models.playback_data import SimulationAttempt, AttemptAnalytics

router = APIRouter()

@router.post("/attempts/fetch")
async def fetch_simulations_attempt(request: dict) -> Dict[str, List[SimulationAttempt]]:
    user_id = request.get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing 'id'")

    service = PlaybackDataService()
    attempts = await service.get_attempts(user_id)
    return {"attempts": attempts}

@router.post("/attempt/fetch")
async def get_sim_attempt_by_id(request: dict) -> Dict[str, AttemptAnalytics]:
    user_id = request.get("userId")
    attempt_id = request.get("attemptId")

    if not user_id:
        raise HTTPException(status_code=400, detail="Missing 'userId'")
    if not attempt_id:
        raise HTTPException(status_code=400, detail="Missing 'attemptId'")

    service = PlaybackDataService()
    attempt = await service.get_attempt_by_id(user_id, attempt_id)
    
    if not attempt:
        raise HTTPException(
            status_code=404,
            detail=f"No attempt found with attemptId={attempt_id} for userId={user_id}"
        )
    
    return {"attempt": attempt}