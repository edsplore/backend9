from fastapi import APIRouter, HTTPException
from typing import Dict, List
from domain.services.playback_service import PlaybackService
from api.schemas.requests import AttemptsRequest, AttemptRequest
from api.schemas.responses import AttemptsResponse, AttemptResponse
from utils.logger import Logger

logger = Logger.get_logger(__name__)

router = APIRouter()

class PlaybackController:
    def __init__(self):
        self.service = PlaybackService()
        logger.info("PlaybackController initialized.")

    async def get_attempts(self, request: AttemptsRequest) -> AttemptsResponse:
        logger.info("Received request to fetch attempts.")
        logger.debug(f"Request data: {request.dict()}")

        try:

            attempts = await self.service.get_attempts(request.user_id)
            logger.info(f"Fetched {len(attempts)} attempts for user {request.user_id}")
            return AttemptsResponse(attempts=attempts)
        except Exception as e:
            logger.error(f"Error fetching attempts: {str(e)}", exc_info=True)
            raise

    async def get_attempt_by_id(self, request: AttemptRequest) -> AttemptResponse:
        logger.info("Received request to fetch attempt by ID.")
        logger.debug(f"Request data: {request.dict()}")

        try:
            attempt = await self.service.get_attempt_by_id(request.user_id, request.attempt_id)

            if not attempt:
                logger.warning(
                    f"No attempt found with attemptId={request.attempt_id} for userId={request.user_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"No attempt found with attemptId={request.attempt_id} for userId={request.user_id}"
                )

            logger.info(f"Attempt with ID {request.attempt_id} retrieved successfully.")
            return AttemptResponse(attempt=attempt)
        except Exception as e:
            logger.error(f"Error fetching attempt by ID: {str(e)}", exc_info=True)
            raise

controller = PlaybackController()

@router.post("/attempts/fetch", tags=["Playback", "Read", "List"])
async def fetch_simulations_attempt(request: dict) -> AttemptsResponse:
    return await controller.get_attempts(AttemptsRequest(user_id=request.get("user_id")))

@router.post("/attempt/fetch", tags=["Playback", "Read"])
async def get_sim_attempt_by_id(request: dict) -> AttemptResponse:
    return await controller.get_attempt_by_id(
        AttemptRequest(user_id=request.get("user_id"), attempt_id=request.get("attempt_id"))
    )