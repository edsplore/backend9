from fastapi import APIRouter, HTTPException
from typing import Dict
from domain.services.simulation_service import SimulationService
from domain.services.chat_service import ChatService
from api.schemas.requests import (CreateSimulationRequest,
                                  UpdateSimulationRequest,
                                  StartAudioSimulationPreviewRequest,
                                  StartChatPreviewRequest,
                                  FetchSimulationsRequest)
from api.schemas.responses import (CreateSimulationResponse,
                                   UpdateSimulationResponse,
                                   StartAudioSimulationPreviewResponse,
                                   StartChatPreviewResponse,
                                   FetchSimulationsResponse)

router = APIRouter()


class SimulationController:

    def __init__(self):
        self.service = SimulationService()
        self.chat_service = ChatService()

    async def create_simulation(
            self,
            request: CreateSimulationRequest) -> CreateSimulationResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.name:
            raise HTTPException(status_code=400, detail="Missing 'name'")
        if not request.division_id:
            raise HTTPException(status_code=400, detail="Missing 'divisionId'")
        if not request.department_id:
            raise HTTPException(status_code=400,
                                detail="Missing 'departmentId'")
        if not request.script:
            raise HTTPException(status_code=400, detail="Missing 'script'")

        result = await self.service.create_simulation(request)
        return CreateSimulationResponse(id=result["id"],
                                        status=result["status"],
                                        prompt=result["prompt"])

    async def update_simulation(
            self, sim_id: str,
            request: UpdateSimulationRequest) -> UpdateSimulationResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")

        result = await self.service.update_simulation(sim_id, request)
        return UpdateSimulationResponse(id=result["id"],
                                        status=result["status"])

    async def start_audio_simulation_preview(
        self, request: StartAudioSimulationPreviewRequest
    ) -> StartAudioSimulationPreviewResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.sim_id:
            raise HTTPException(status_code=400, detail="Missing 'simId'")

        result = await self.service.start_audio_simulation_preview(
            request.sim_id, request.user_id)
        return StartAudioSimulationPreviewResponse(
            access_token=result["access_token"])

    async def start_chat_preview(
            self,
            request: StartChatPreviewRequest) -> StartChatPreviewResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")
        if not request.sim_id:
            raise HTTPException(status_code=400, detail="Missing 'simId'")

        result = await self.chat_service.start_chat(request.user_id,
                                                    request.sim_id,
                                                    request.message)
        return StartChatPreviewResponse(response=result["response"])

    async def fetch_simulations(
            self,
            request: FetchSimulationsRequest) -> FetchSimulationsResponse:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Missing 'userId'")

        simulations = await self.service.fetch_simulations(request.user_id)
        return FetchSimulationsResponse(simulations=simulations)


controller = SimulationController()


@router.post("/simulations/create")
async def create_simulation(
        request: CreateSimulationRequest) -> CreateSimulationResponse:
    return await controller.create_simulation(request)


@router.put("/simulations/{sim_id}/update")
async def update_simulation(
        sim_id: str,
        request: UpdateSimulationRequest) -> UpdateSimulationResponse:
    return await controller.update_simulation(sim_id, request)


@router.post("/simulations/start-audio-preview")
async def start_audio_simulation_preview(
    request: StartAudioSimulationPreviewRequest
) -> StartAudioSimulationPreviewResponse:
    return await controller.start_audio_simulation_preview(request)


@router.post("/simulations/start-chat-preview")
async def start_chat_preview(
        request: StartChatPreviewRequest) -> StartChatPreviewResponse:
    return await controller.start_chat_preview(request)


@router.post("/simulations/fetch")
async def fetch_simulations(
        request: FetchSimulationsRequest) -> FetchSimulationsResponse:
    return await controller.fetch_simulations(request)
