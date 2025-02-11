from fastapi import APIRouter, HTTPException
from domain.services.voice_service import VoiceService
from api.schemas.requests import ListVoicesRequest
from api.schemas.responses import ListVoicesResponse

router = APIRouter()

class VoiceController:
    def __init__(self):
        self.service = VoiceService()

    async def list_voices(self, request: ListVoicesRequest) -> ListVoicesResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")

        voices = await self.service.list_voices()
        return ListVoicesResponse(voices=voices)

controller = VoiceController()

@router.post("/list-voices")
async def list_voices(request: ListVoicesRequest) -> ListVoicesResponse:
    return await controller.list_voices(request)