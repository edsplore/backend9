from fastapi import APIRouter, HTTPException
from domain.services.voice_service import VoiceService
from api.schemas.requests import ListVoicesRequest
from api.schemas.responses import ListVoicesResponse
from utils.logger import Logger

logger = Logger.get_logger(__name__)
router = APIRouter()


class VoiceController:

    def __init__(self):
        self.service = VoiceService()
        logger.info("VoiceController initialized.")

    async def list_voices(self,
                          request: ListVoicesRequest) -> ListVoicesResponse:
        logger.info("Received request to list voices.")
        logger.debug(f"Request data: {request.dict()}")

        try:

            voices = await self.service.list_voices()
            logger.info(f"Fetched {len(voices)} voices successfully.")
            return ListVoicesResponse(voices=voices)
        except Exception as e:
            logger.error(f"Error listing voices: {str(e)}", exc_info=True)
            raise


controller = VoiceController()


@router.post("/list-voices", tags=["Voices", "Read"])
async def list_voices(request: ListVoicesRequest) -> ListVoicesResponse:
    logger.info("API called: /list-voices")
    return await controller.list_voices(request)
