from fastapi import APIRouter, HTTPException
from typing import Dict, List
from domain.services.playback_service import PlaybackService
from api.schemas.requests import AttemptsRequest, AttemptRequest
from api.schemas.responses import AttemptsResponse, AttemptResponse

router = APIRouter()

class PlaybackController:
    def __init__(self):
        self.service = PlaybackService()

    async def get_attempts(self, request: AttemptsRequest) -> AttemptsResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'id'")
        attempts = await self.service.get_attempts(request.user_id)
        return AttemptsResponse(attempts=attempts)

    async def get_attempt_by_id(self, request: AttemptRequest) -> AttemptResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.attempt_id:
            raise HTTPException(status_code=400, detail="Missing 'attemptId'")

        attempt = await self.service.get_attempt_by_id(request.user_id, request.attempt_id)
        if not attempt:
            raise HTTPException(
                status_code=404,
                detail=f"No attempt found with attemptId={request.attempt_id} for userId={request.user_id}"
            )
        return AttemptResponse(attempt=attempt)

controller = PlaybackController()

@router.post("/attempts/fetch", tags=["Playback", "Read", "List"])
async def fetch_simulations_attempt(request: dict) -> AttemptsResponse:
    return await controller.get_attempts(AttemptsRequest(user_id=request.get("id")))

@router.post("/attempt/fetch", tags=["Playback", "Read"])
async def get_sim_attempt_by_id(request: dict) -> AttemptResponse:
    return await controller.get_attempt_by_id(
        AttemptRequest(user_id=request.get("userId"), attempt_id=request.get("attemptId"))
    )